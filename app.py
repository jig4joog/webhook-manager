import streamlit as st
from db import SessionLocal, init_db
from models import Group, Service, GroupService
from sqlalchemy import select, update, DateTime
from datetime import datetime
import re
from db_migrate import seed_initial_data   # optional helper

def ensure_db():
    # 1) create tables if needed
    init_db()

    # 2) optional: if this is a fresh DB, seed it once
    session = SessionLocal()
    has_groups = session.query(Group).first() is not None
    if not has_groups:
        # call a seed function or inline your seeding logic here
        seed_initial_data(session)
        pass
    session.close()

ensure_db()

def make_key(name: str) -> str:
    key = name.strip().lower()
    key = re.sub(r'[^a-z0-9]+', '-', key)
    key = re.sub(r'-+', '-', key).strip('-')
    return key

init_db()
session = SessionLocal()

st.title("Discord Webhook Manager")

def load_and_display_groups():
    groups = session.query(Group).all()

    for k in ["new_name", "new_color", "new_img"]:
        if k not in st.session_state:
            st.session_state[k] = ""

    if st.session_state.get("clear_new_group_form"):
        for k in ["new_name", "new_color", "new_img"]:
            st.session_state[k] = ""
        st.session_state["clear_new_group_form"] = False

    st.markdown("## Add New Group")

    all_services = session.query(Service).all()

    with st.form("add_group_form"):
        new_name = st.text_input("Display Name", key="new_name")
        new_color = st.text_input("Color (hex, e.g. FF0000)", key="new_color")
        new_img = st.text_input("Footer Image URL", key="new_img")

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

    for group in groups:

        # This is the expander code
        with st.expander(f"{group.name} (ID {group.id})", expanded=False):
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

            #Add Services to this group section
            all_services = session.query(Service).all()
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

            #Services and Markdowns
            st.markdown(f"<h2 style='margin-bottom:0'>{group.name}</h2>", unsafe_allow_html=True)
            st.markdown("#### Services:")

            # for gs in group.group_services:
            for i, gs in enumerate(group.group_services):
                # 4 columns: name | status | toggle | webhook update stuff
                cols = st.columns([2, 1, 1, 3])
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

                    # Form to edit the URL (stage change only)
                    with st.form(key=f"webhook_form_{group.id}_{gs.service.id}"):
                        updated_url = st.text_input(
                            "Webhook URL",
                            value=gs.webhook_url or "",
                            label_visibility="collapsed",
                            placeholder="https://discord.com/api/webhooks/...",
                        )

                        if st.form_submit_button("Update Webhook"):
                            # Store proposed value, but do NOT write to DB yet
                            st.session_state[pending_key] = updated_url

                    # If there is a pending change, show confirmation UI
                    if pending_key in st.session_state and st.session_state[pending_key]:
                        st.warning(
                            f"Confirm changing webhook for {gs.service.name} to:\n"
                            f"{st.session_state[pending_key]}"
                        )
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Confirm change", key=f"confirm_{group.id}_{gs.service.id}"):
                                gs.webhook_url = st.session_state[pending_key]
                                gs.webhook_updated_at = datetime.utcnow()
                                session.commit()
                                st.session_state[pending_key] = ""
                                st.success("Webhook updated.")
                                st.rerun()
                        with c2:
                            if st.button(
                                    "Cancel",
                                    key=f"cancel_{group.id}_{gs.service.id}",
                            ):
                                st.session_state[pending_key] = ""

# .venv\Scripts\Activate
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# streamlit run app.py

if __name__ == "__main__":
    load_and_display_groups()
