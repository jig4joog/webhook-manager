import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # Loads environment variables from a .env file

from db import SessionLocal, init_db
from models import Group, Service, GroupService
from sqlalchemy import select, update, DateTime, or_
from datetime import datetime
import re
import csv
import io
import requests
from db_migrate import seed_initial_data   # optional helper
from check_webhooks import check_all_webhooks
import pandas as pd
from sqlalchemy.orm import joinedload
import time

# start_time = time.time()
# st.write(f"Script start: 0s")
@st.cache_resource
def get_db_connection():
    """
    Creates the DB engine and checks tables ONLY ONCE.
    Streamlit will keep this result in memory, so clicking buttons
    won't trigger a 2-second database handshake.
    """
    # 1. Create tables (expensive operation)
    init_db()

    # 2. Seed data if needed
    db = SessionLocal()
    try:
        if not db.query(Group).first():
            seed_initial_data(db)
    finally:
        db.close()
    return True


# Initialize once
get_db_connection()

def make_key(name: str) -> str:
    key = name.strip().lower()
    key = re.sub(r'[^a-z0-9]+', '-', key)
    key = re.sub(r'-+', '-', key).strip('-')
    return key


def make_group_csv_bytes(group):
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "group_id",
        "group_name",
        "service_id",
        "service_name",
        "enabled",
        "webhook_url",
        "webhook_updated_at",
        "status_changed_at",
    ])

    # Data rows
    for gs in group.group_services:
        writer.writerow([
            group.id,
            group.name,
            gs.service_id,
            gs.service.name,
            "TRUE" if gs.enabled else "FALSE",
            gs.webhook_url or "",
            gs.webhook_updated_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(gs, "webhook_updated_at", None) else "",
            gs.status_changed_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(gs, "status_changed_at", None) else "",
        ])

    csv_str = output.getvalue()
    output.close()
    return csv_str.encode("utf-8")

def send_discord_message(webhook_url: str, content: str, username: str | None = None):
    if not webhook_url or not content:
        return

    data = {
        "content": content,
    }
    if username:
        data["username"] = username

    try:
        resp = requests.post(webhook_url, json=data, timeout=5)
        # Discord usually returns 204 for success
        if not (200 <= resp.status_code < 300):
            print(f"Discord webhook error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Failed to send Discord webhook: {e}")

st.set_page_config(
    page_title="Discord Webhook Manager",
    layout="wide",
    initial_sidebar_state="expanded",
)

def health_check_button():
    # Initialize state variable if it doesn't exist
    if "health_scan_results" not in st.session_state:
        st.session_state["health_scan_results"] = None

    st.markdown("### Health Check")

    col_scan, col_clear = st.columns([2, 5])

    with col_scan:
        # The button to trigger the DB query
        if st.button("🔍 Scan for broken webhooks"):
            check_all_webhooks()

            with st.spinner("Checking database records..."):
                # Run the query ONLY when button is clicked
                broken_query = (
                    session.query(GroupService)
                    .options(
                        joinedload(GroupService.group),
                        joinedload(GroupService.service)
                    )
                    .filter(
                        GroupService.enabled.is_(True),
                        or_(
                            GroupService.health_status == "missing",
                            GroupService.health_status == "error",
                        )
                    )
                    .all()
                )

                # Convert complex DB objects to simple dictionaries for session_state
                # (This prevents crashes when the DB session closes)
                results = []
                for gs in broken_query:
                    results.append({
                        "group_name": gs.group.name,
                        "service_name": gs.service.name,
                        "status": gs.health_status,
                        "code": gs.health_code,
                        "checked_at": gs.health_checked_at
                    })

                st.session_state["health_scan_results"] = results

                if not results:
                    st.toast("✅ No broken webhooks found!", icon="🎉")

    # Display the results if they exist in state
    broken_data = st.session_state["health_scan_results"]

    if broken_data:
        # Show a "Clear" button to hide the panel
        with col_clear:
            if st.button("Clear results"):
                st.session_state["health_scan_results"] = None
                st.rerun()

        st.markdown(
            f"""
                <div style="
                    background-color:#FEF2F2;
                    border:1px solid #FCA5A5;
                    border-radius:8px;
                    padding:10px 14px;
                    margin-bottom:16px;
                    margin-top: 10px;
                ">
                  <div style="font-weight:600;color:#B91C1C;margin-bottom:4px;">
                    🚨 Found {len(broken_data)} broken webhooks
                  </div>
                  <div style="font-size:13px;color:#7F1D1D;">
                    Based on last known health check.
                  </div>
                </div>
                """,
            unsafe_allow_html=True,
        )

        with st.expander(f"View Details ({len(broken_data)})", expanded=True):
            for item in broken_data:
                ts = item['checked_at'].strftime("%Y-%m-%d %H:%M:%S UTC") if item['checked_at'] else "never"
                status_label = item['status'] or "unknown"
                code_label = item['code'] if item['code'] is not None else "—"

                c1, c2, c3 = st.columns([3, 2, 3])

                with c1:
                    st.markdown(
                        f"**{item['group_name']}**  \n"
                        f"<span style='font-size:12px;color:#6B7280'>{item['service_name']}</span>",
                        unsafe_allow_html=True,
                    )

                with c2:
                    color = "#B91C1C"  # Red text
                    st.markdown(
                        f"<span style='font-size:12px;"
                        f"padding:2px 8px;border-radius:999px;"
                        f"background-color:#FEE2E2;color:{color};'>"
                        f"{status_label.upper()} &middot; {code_label}"
                        f"</span>",
                        unsafe_allow_html=True,
                    )

                with c3:
                    st.markdown(
                        f"<span style='font-size:12px;color:#6B7280'>"
                        f"Last checked: {ts}"
                        f"</span>",
                        unsafe_allow_html=True,
                    )

                st.markdown("<hr style='margin:6px 0 8px 0;'>", unsafe_allow_html=True)

session = SessionLocal()

st.title("Discord Webhook Manager")

def load_and_display_groups():
    st.markdown("<a id='top'></a>", unsafe_allow_html=True)  # Anchor for the button

    health_check_button()
    # 1. Fetch ALL Services and their links in one go
    # We use joinedload so counting links in the "Service Overview" doesn't trigger more queries
    all_services = (
        session.query(Service)
        .options(joinedload(Service.group_services))
        .order_by(Service.name.asc())
        .all()
    )
    # st.write(f"Services loaded: {time.time() - start_time:.2f}s")
    all_services = sorted(all_services, key=lambda s: s.name.lower())

    # NEW: load services once, before anything else
    for k in ["new_name", "new_color", "new_img"]:
        if k not in st.session_state:
            st.session_state[k] = ""

    if st.session_state.get("clear_new_group_form"):
        for k in ["new_name", "new_color", "new_img"]:
            st.session_state[k] = ""
        st.session_state["clear_new_group_form"] = False

    # expander / toggle for advanced controls
    with st.expander("Advanced actions"):
        st.checkbox(
            "Show admin tools",
            key="show_admin_tools",
            help="Enable extra delete/disable controls",
        )

    show_tools = st.session_state.get("show_admin_tools", False)

    # Service Overview (put this after all_services is defined)
    st.markdown("## Service Overview")
    with st.expander(f"Services", expanded=False):

        service_rows = []
        for svc in all_services:
            total_links = len(svc.group_services)
            enabled_links = sum(1 for gs in svc.group_services if gs.enabled)
            service_rows.append((svc, total_links, enabled_links))

        for svc, total_links, enabled_links in service_rows:
            enabled_badge = f"{enabled_links}/{total_links} active" if total_links else "0 routed"
            status_color = "#16a34a" if enabled_links else "#6b7280"

            left, right = st.columns([5, 2])

            with left:
                st.markdown(
                    f"""
                    <div style="
                        border: 1px solid #e5e7eb;
                        border-radius: 6px;
                        padding: 8px 10px;
                        margin-bottom: 4px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        font-size: 13px;
                    ">
                      <div>
                        <div style="font-weight: 600;">{svc.name}</div>
                        <div style="color: #6b7280;">
                          Linked groups: <b>{total_links}</b>
                        </div>
                      </div>
                      <div style="
                          padding: 2px 8px;
                          border-radius: 999px;
                          background-color: {status_color};
                          color: white;
                          font-size: 12px;
                      ">
                        {enabled_badge}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with right:
                # three tight buttons: Remove links | Enable/Disable all | Delete service (admin)
                btn1, btn2, btn3 = st.columns([1, 1, 1])
                # Remove all links (existing behavior)
                with btn1:
                    confirm_key_links = f"confirm_delete_service_links_{svc.id}"
                    if st.button("Remove links", key=f"delete_service_links_{svc.id}"):
                        st.session_state[confirm_key_links] = True
                
                # Toggle enable/disable across all groups for this service
                toggle_key = f"confirm_toggle_service_{svc.id}"
                toggle_label = "Disable all" if enabled_links else "Enable all"
                with btn2:
                    if st.button(toggle_label, key=f"toggle_service_{svc.id}"):
                        st.session_state[toggle_key] = True

                # Delete service (admin)
                if show_tools:
                    with btn3:
                        confirm_key_service = f"confirm_delete_service_{svc.id}"
                        if st.button("Delete Service", key=f"delete_service_{svc.id}"):
                            st.session_state[confirm_key_service] = True

            # Confirmation for Remove links
            if st.session_state.get(f"confirm_delete_service_links_{svc.id}"):
                st.warning(f"Remove **all links** for {svc.name}? This detaches it from every group.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes, delete all", key=f"yes_confirm_delete_links_{svc.id}"):
                        for gs in list(svc.group_services):
                            session.delete(gs)
                        session.commit()
                        st.session_state[f"confirm_delete_service_links_{svc.id}"] = False
                        st.rerun()
                with c2:
                    if st.button("Cancel", key=f"no_confirm_delete_links_{svc.id}"):
                        st.session_state[f"confirm_delete_service_links_{svc.id}"] = False
                        st.rerun()

            # Confirmation & execution for Toggle enable/disable service across all groups
            if st.session_state.get(toggle_key):
                action = "disable" if enabled_links else "enable"
                st.warning(f"⚠️ Are you sure you want to {action.upper()} '{svc.name}' for ALL groups?")
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button("Yes, do it", key=f"yes_toggle_{svc.id}"):
                        now = datetime.utcnow()
                        created = 0
                        updated = 0
                        if enabled_links:
                            # Disable existing links
                            for gs in list(svc.group_services):
                                if gs.enabled:
                                    gs.enabled = False
                                    gs.status_changed_at = now
                                    updated += 1
                        else:
                            # Enable existing links and create missing links for groups
                            all_groups = session.query(Group).all()
                            existing_by_group = {gs.group_id: gs for gs in list(svc.group_services)}
                            for g in all_groups:
                                if g.id in existing_by_group:
                                    gs = existing_by_group[g.id]
                                    if not gs.enabled:
                                        gs.enabled = True
                                        gs.status_changed_at = now
                                        updated += 1
                                else:
                                    new_link = GroupService(group_id=g.id, service_id=svc.id, enabled=True, status_changed_at=now)
                                    session.add(new_link)
                                    created += 1

                        if created or updated:
                            session.commit()
                        st.session_state[toggle_key] = False
                        st.toast(f"{svc.name} {'disabled' if enabled_links else 'enabled'} for all groups "
                                 f"({created} created, {updated} updated)" if (created or updated) else "No changes made.")
                        st.rerun()
                with c_no:
                    if st.button("Cancel", key=f"no_toggle_{svc.id}"):
                        st.session_state[toggle_key] = False
                        st.rerun()

            if show_tools:
                confirm_key_del_svc = f"confirm_delete_service_{svc.id}"
                if st.session_state.get(confirm_key_del_svc):
                    st.warning(f"⚠️ **PERMANENTLY DELETE** service **{svc.name}** and all its links? This cannot be undone.")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes, DELETE", key=f"yes_{confirm_key_del_svc}"):
                            # First delete all associated links
                            for gs in list(svc.group_services):
                                session.delete(gs)
                            
                            # Then delete the service itself
                            session.delete(svc)
                            session.commit()
                            
                            st.session_state[confirm_key_del_svc] = False
                            st.toast(f"Service '{svc.name}' permanently deleted.", icon="🗑️")
                            st.rerun()
                    with c2:
                        if st.button("Cancel", key=f"no_{confirm_key_del_svc}"):
                            st.session_state[confirm_key_del_svc] = False
                            st.rerun()

    if show_tools:
        st.markdown("## Manage Services")

        with st.form("add_service_form"):
            new_service_name = st.text_input("New service name")
            add_service_submitted = st.form_submit_button("Add service")

        if add_service_submitted and new_service_name:
            # Only create if not already present
            existing = session.query(Service).filter(Service.name == new_service_name).first()
            if existing is None:
                session.add(Service(name=new_service_name))
                session.commit()
                st.success(f"Service '{new_service_name}' added.")
                st.rerun()
            else:
                st.warning("Service with that name already exists.")

        # all_services = session.query(Service).all()
        st.write("Existing services:", ", ".join(sorted((s.name for s in all_services))))

        st.markdown("## Add New Group")

        # all_services = session.query(Service).all()

        with st.form("add_group_form"):
            new_name = st.text_input("Display Name", key="new_name")
            new_color = st.text_input("Color (hex, e.g. FF0000)", key="new_color")
            new_img = st.text_input("Footer Image URL", key="new_img")
            new_caption = st.text_input("Caption / notes", key="new_caption",placeholder="e.g. Friends group, Members only, etc.")
            mode = st.radio(
                "Onboard services as:",
                ["All services", "Choose services later"],
                horizontal=True,
                key="new_group_svc_mode",
            )

            submitted = st.form_submit_button("Create Group")

        if submitted and new_name:
            internal_key = make_key(new_name)
            footer = f"{new_name} | Developed by bennybags#0344"

            group = Group(
                name=new_name,
                color=new_color,
                webhook_footer=footer,
                webhook_footer_img=new_img,
                webhook_url=None,  # no default webhook for the group
                enabled=True,
                caption=new_caption,
            )
            session.add(group)
            session.commit()

            if mode == "All services":
                links = [
                    GroupService(group_id=group.id, service_id=s.id, enabled=False)
                    for s in all_services
                ]
                if links:
                    session.add_all(links)
                    session.commit()

            st.session_state["clear_new_group_form"] = True
            st.success("New group created.")
            st.rerun()

    # --- NEW GROUP SELECTION ---
    st.markdown("### Select a Group")
    # Fetch group objects for the selectbox, which is a fast query
    groups_for_selection = session.query(Group).order_by(Group.name.asc()).all()
    # Add a placeholder for the default option
    group_options = ["-- Select a group to manage --"] + groups_for_selection

    def format_group_for_display(g):
        if not isinstance(g, Group):
            return g  # This is for the "-- Select..." placeholder
        
        display_text = g.name
        if g.caption:
            display_text += f" | {g.caption.strip()}"
        return display_text

    selected_option = st.selectbox(
        "Choose a group to view or edit its webhooks",
        options=group_options,
        format_func=format_group_for_display,  # Show name and caption
        key="group_selector",
    )

    if not isinstance(selected_option, Group):
        st.info("Select a group from the dropdown above to see its details and manage services.")
    else:
        # A group object was selected, so we use its ID to fetch the full details.
        # This prevents the MultipleResultsFound error if names are duplicated.
        group = (
            session.query(Group)
            .options(
                # This fetches the Group -> GroupService link
                joinedload(Group.group_services)
                # This fetches the GroupService -> Service details
                .joinedload(GroupService.service)
            )
            .filter(Group.id == selected_option.id)
            .one()
        )

        st.markdown("## Group Details")

        cap = (group.caption or "").strip()
        label = f"{group.name}" if not cap else f"{group.name} | {cap}"
        # Removed expander for each group as only one is displayed
        st.caption(f"Group ID: {group.id} | Group Caption: {group.caption}")
        any_enabled = any(gs.enabled for gs in group.group_services)
        status_text = "Enabled" if any_enabled else "Disabled"
        bar_color = "16a34a" if any_enabled else "dc2626"  # green / red

        st.markdown(
            f"""
            <div style="
                background-color: #{bar_color};
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                margin-bottom: 6px;
                font-size: 13px;
                display: flex;
                justify-content: space-between;
            ">
                <span>{group.name}</span>
                <span>{status_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # NEW: group-level toggle
        # 1. Logic to determine label
        group_toggle_label = "Disable all services" if any_enabled else "Enable all services"

        # 2. Define a unique key for this group's confirmation state
        confirm_key = f"confirm_toggle_all_{group.id}"

        # 3. Main Trigger Button
        if st.button(group_toggle_label, key=f"group_toggle_btn_{group.id}"):
            st.session_state[confirm_key] = True

        # 4. Confirmation UI (Only shows if triggered)
        if st.session_state.get(confirm_key):
            action_word = "DISABLE" if any_enabled else "ENABLE"
            st.warning(f"⚠️ Are you sure you want to **{action_word}** all services for **{group.name}**?")

            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button("Yes, do it", key=f"yes_toggle_{group.id}"):
                    # --- EXECUTE LOGIC ---
                    now = datetime.utcnow()
                    for gs in group.group_services:
                        gs.enabled = not any_enabled  # flip to opposite
                        gs.status_changed_at = now

                        # Optional: Send Discord notification if disabling
                        if not gs.enabled and gs.webhook_url:
                            send_discord_message(
                                gs.webhook_url,
                                f"Service Announcement\n\n🔕 Webhook disabled for **{gs.group.name} / {gs.service.name}**.\n\nPlease contact your provider (bennybags#0344) to re-enable services.",
                                username="Webhook Manager"
                            )

                    session.commit()

                    # Cleanup state and refresh
                    st.session_state[confirm_key] = False
                    st.success(f"All services {action_word.lower()}d.")
                    st.rerun()

            with col_cancel:
                if st.button("Cancel", key=f"no_toggle_{group.id}"):
                    st.session_state[confirm_key] = False
                    st.rerun()

        #Add Services to this group section
        # all_services = session.query(Service).all()
        st.markdown("### Add services to this group")

        mode = st.radio(
            "How do you want to add services?",
            ["All services", "Choose services"],
            key=f"svc_mode_{group.id}",
            horizontal=True,
        )

        if mode == "All services":
            if st.button("Link all services", key=f"link_all_{group.id}"):
                existing_ids = {gs.service_id for gs in group.group_services}
                new_links = [
                    GroupService(group_id=group.id, service_id=s.id, enabled=False)
                    for s in all_services
                    if s.id not in existing_ids
                ]
                if new_links:
                    session.add_all(new_links)
                    session.commit()
                    st.success("All services linked to this group.")
                    st.rerun()
                else:
                    st.info("All services are already linked to this group.")
        else:
            # multi-select of services not yet linked
            existing_ids = {gs.service_id for gs in group.group_services}
            available = [s for s in all_services if s.id not in existing_ids]

            selected = st.multiselect(
                "Select services to add",
                options=available,
                format_func=lambda s: s.name,
                key=f"svc_select_{group.id}",
            )

            if st.button("Add selected services", key=f"add_selected_{group.id}"):
                new_links = [
                    GroupService(group_id=group.id, service_id=s.id, enabled=False)
                    for s in selected
                ]
                if new_links:
                    session.add_all(new_links)
                    session.commit()
                    st.success("Selected services linked.")
                    st.rerun()
                else:
                    st.info("No services selected.")

        # csv_bytes = make_group_csv_bytes(group)
        # st.download_button(
        #     label="Export group to CSV",
        #     data=csv_bytes,
        #     file_name=f"group_{group.id}_{group.name}.csv",
        #     mime="text/csv",
        #     key=f"export_group_{group.id}",
        # )

        settings_key = f"show_group_settings_{group.id}"
        with st.expander(f"Group settings for {group.name}", expanded=False):

            col1, col2 = st.columns(2)

            with col1:
                new_name = st.text_input(
                    "Display name",
                    value=group.name,
                    key=f"name_{group.id}",
                )
                new_color = st.text_input(
                    "Color (hex, e.g. FF0000)",
                    value=group.color or "",
                    key=f"color_{group.id}",
                )
                new_footer = st.text_input(
                    "Footer (| Developed by bennybags#0344)",
                    value=group.webhook_footer or "",
                    key=f"webook_footer{group.id}",
                )

            with col2:
                new_img = st.text_input(
                    "Footer image URL",
                    value=group.webhook_footer_img or "",
                    key=f"img_{group.id}",
                )
                new_caption = st.text_input(
                    "Caption / notes",
                    value=group.caption or "",
                    key=f"caption_{group.id}",
                )
                # if group.webhook_footer_img:
                #     st.image(group.webhook_footer_img, width=80, caption="Current footer image")

            # last updated timestamp
            if getattr(group, "updated_at", None):
                st.caption(f"Last updated: {group.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

            if st.button("Save group settings", key=f"save_group_{group.id}"):
                group.name = new_name.strip()
                group.webhook_footer = new_footer.strip()
                group.color = new_color.strip() or None
                group.webhook_footer_img = new_img.strip() or None
                group.caption = new_caption.strip() or None
                session.commit()
                st.rerun()

        #Services and Markdowns
        st.markdown(f"<h2 style='margin-bottom:0'>{group.name}</h2>", unsafe_allow_html=True)
        st.markdown("#### Services:")

        # sort links for this group by service name (A→Z)
        sorted_links = sorted(
            group.group_services,
            key=lambda gs: gs.service.name.lower()
        )

        # for gs in group.group_services:
        for i, gs in enumerate(sorted_links):
            # 4 columns: name | status | toggle | webhook update stuff
            cols = st.columns([1, 1, 1, 3, 0.6])

            #Service name
            with cols[0]:
                st.markdown(f"**{gs.service.name}**")
                if gs.webhook_updated_at:
                    st.markdown(
                        f"<span style='font-size:13px;color:#999'>Last updated: "
                        f"{gs.webhook_updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</span>",
                        unsafe_allow_html=True,
                    )
            #Enable Button
            with cols[1]:
                st.markdown("🟢" if gs.enabled else "🔴")
                st.markdown("Enabled" if gs.enabled else "Disabled")
                if gs.status_changed_at:
                    st.markdown(
                        f"<span style='font-size:11px;color:#999'>"
                        f"Last change: {gs.status_changed_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                        f"</span>",
                        unsafe_allow_html=True,
                    )
            #Disable Button
            with cols[2]:
                toggle_txt = "Disable" if gs.enabled else "Enable"
                if st.button(toggle_txt, key=f"toggle_{group.id}_{gs.service.id}_{gs.enabled}"):
                    gs.enabled = not gs.enabled
                    gs.status_changed_at = datetime.utcnow()
                    session.commit()
                    st.rerun()
            #Updating Section
            with cols[3]:
                st.markdown(
                    f"<span style='font-size:13px;color:#666'>Webhook for <b>{gs.service.name}</b>:</span>",
                    unsafe_allow_html=True,
                )

                pending_key = f"pending_webhook_{group.id}_{gs.service.id}"

                confirm_key = f"confirm_clear_{group.id}_{gs.service.id}"

                with st.form(key=f"webhook_form_{group.id}_{gs.service.id}"):
                    updated_url = st.text_input(
                        "Webhook URL",
                        value=gs.webhook_url or "",
                        label_visibility="collapsed",
                        placeholder="https://discord.com/api/webhooks/...",
                    )

                    col_u, col_r = st.columns([2, 2])
                    with col_u:
                        update_clicked = st.form_submit_button("Update Webhook")
                    with col_r:
                        remove_clicked = st.form_submit_button("Remove webhook")

                    # Handle update
                    if update_clicked:
                        st.session_state[pending_key] = updated_url

                    # Handle remove with double confirmation
                    if remove_clicked:
                        if not st.session_state.get(confirm_key, False):
                            st.session_state[confirm_key] = True
                            st.warning("Click 'Remove webhook' again to confirm.")
                        else:
                            gs.webhook_url = None
                            gs.health_status = "unconfigured"  # or your chosen state
                            gs.webhook_updated_at = None
                            session.commit()
                            st.success("Webhook removed.")
                            st.session_state[confirm_key] = False

                # If there is a pending change, show confirmation UI
                if pending_key in st.session_state and st.session_state[pending_key]:
                    st.warning(
                        f"Confirm changing webhook for {gs.service.name} to:\n"
                        f"{st.session_state[pending_key]}"
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Confirm change", key=f"confirm_{group.id}_{gs.service.id}"):
                            new_url = st.session_state[pending_key].strip()

                            try:
                                resp = requests.get(new_url, timeout=5)
                                code = resp.status_code

                                if 200 <= code < 300:
                                    # valid -> save to DB and mark health
                                    gs.webhook_url = new_url
                                    gs.webhook_updated_at = datetime.utcnow()
                                    gs.health_status = "ok"
                                    gs.health_code = code
                                    gs.health_checked_at = datetime.utcnow()

                                    session.commit()
                                    st.session_state[pending_key] = ""
                                    st.success(f"Webhook updated and looks valid (HTTP {code}).")
                                    st.rerun()
                                elif code in (401, 404):
                                    st.error(
                                        f"Discord returned {code}: webhook appears invalid or deleted. Not saved.")
                                else:
                                    st.error(f"Discord returned HTTP {code}. Not saving this URL.")
                            except Exception:
                                st.error("Error reaching Discord; webhook not saved.")

                    with c2:
                        if st.button("Cancel", key=f"cancel_{group.id}_{gs.service.id}"):
                            st.session_state[pending_key] = ""

            # delete this service from this group
            with cols[4]:
                confirm_key = f"confirm_delete_link_{group.id}_{gs.service.id}"

                if st.button("🗑️", key=f"delete_link_{group.id}_{gs.service.id}"):
                    st.session_state[confirm_key] = True

            if st.session_state.get(confirm_key):
                st.warning("Remove this service from this group?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes, delete", key=f"yes_{confirm_key}"):
                        session.delete(gs)
                        session.commit()
                        st.session_state[confirm_key] = False
                        st.rerun()
                with c2:
                    if st.button("Cancel", key=f"no_{confirm_key}"):
                        st.session_state[confirm_key] = False

    # Add the "Back to Top" button at the end of the page rendering
    st.markdown("""
        <style>
            .back-to-top {
                position: fixed;
                bottom: 25px;
                right: 25px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background-color: #313336;
                color: white;
                padding: 10px;
                font-size: 18px;
                border-radius: 50%;
                text-decoration: none;
                z-index: 1000;
                border: 2px solid #fff;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                transition: background-color 0.3s, transform 0.2s;
            }
            .back-to-top:hover {
                background-color: #4f545c;
                color: white;
                transform: scale(1.1);
            }
        </style>
        <a href="#top" class="back-to-top" title="Back to Top">
            ⬆️
        </a>
    """, unsafe_allow_html=True)

# .venv\Scripts\Activate
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# streamlit run home.py
# broken url = 'https://discord.com/api/webhooks/1444080766140022814/pEKP8d0-Vh1zydGTl9Idz375b8D1hpDgzFyv6x9lHX4I2_m072FQLBKIpruz46FrMTKS'

if __name__ == "__main__":
    try:
        load_and_display_groups()
    finally:
        # Crucial: Always close the connection when the script finishes rendering
        session.close()