import streamlit as st
from db import SessionLocal, init_db
from models import Group, Service, GroupService
from sqlalchemy import select

init_db()
session = SessionLocal()

st.title("Discord Webhook Manager")

def toggle_group(group_id):
    group = session.query(Group).get(group_id)
    group.enabled = not group.enabled
    session.commit()
    st.rerun()

def delete_group(group_id):
    group = session.query(Group).get(group_id)
    session.delete(group)
    session.commit()
    st.rerun()

groups = session.query(Group).all()

# for group in groups:
#     st.header(group.name)
#     st.markdown("Services:")
#
#     # Enable All / Disable All buttons
#     all_enabled = all(gs.enabled for gs in group.group_services)
#     if st.button(f"{'Disable All' if all_enabled else 'Enable All'}", key=f"group_toggle_{group.id}"):
#         for gs in group.group_services:
#             gs.enabled = not all_enabled  # If all are enabled, disable; else enable all
#         session.commit()
#         st.rerun()
#
#     # Per-service enable/disable UI
#     for gs in group.group_services:
#         st.write(f"- {gs.service.name} {'🟢 Enabled' if gs.enabled else '🔴 Disabled'}")
#         if st.button(
#             f"{'Disable' if gs.enabled else 'Enable'} {gs.service.name}",
#             key=f"toggle_{group.id}_{gs.service.id}"
#         ):
#             gs.enabled = not gs.enabled
#             session.commit()
#             st.rerun()
#     st.markdown("---")
# 🟢
for group in groups:
    st.markdown(f"<h2 style='margin-bottom:0'>{group.name}</h2>", unsafe_allow_html=True)
    st.markdown("#### Services:")

    for gs in group.group_services:
        # 4 columns: name | status | toggle | webhook update stuff
        cols = st.columns([2, 1, 1, 3])
        with cols[0]:
            st.markdown(f"**{gs.service.name}**")
        with cols[1]:
            st.markdown("🟢" if gs.enabled else "🔴")
            st.markdown("Enabled" if gs.enabled else "Disabled")
        with cols[2]:
            toggle_txt = "Disable" if gs.enabled else "Enable"
            if st.button(f"{toggle_txt}", key=f"toggle_{group.id}_{gs.service.id}_{gs.enabled}"):
                gs.enabled = not gs.enabled
                session.commit()
                st.rerun()
        with cols[3]:
            st.markdown(f"<span style='font-size:13px;color:#666'>Webhook for <b>{gs.service.name}</b>:</span>", unsafe_allow_html=True)
            updated_url = st.text_input(
                "",
                value=gs.webhook_url if gs.webhook_url else "",
                key=f"webhook_input_{group.id}_{gs.service.id}"
            )
            # Button and input on the same column/row
            change_btn = st.button(
                "Update Webhook",
                key=f"update_webhook_{group.id}_{gs.service.id}"
            )
            if change_btn:
                gs.webhook_url = updated_url
                session.commit()
                st.success("Webhook updated!")
                st.rerun()
    st.markdown("<hr style='margin-top:20px;margin-bottom:20px;'>", unsafe_allow_html=True)




groups = session.query(Group).all()

with st.form("add_group"):
    new_key = st.text_input("Internal Key")
    new_name = st.text_input("Display Name")
    new_footer = st.text_input("Footer")
    new_color = st.text_input("Color")
    new_img = st.text_input("Footer Image URL")
    new_url = st.text_input("Webhook URL")
    submitted = st.form_submit_button("Add Group")
    if submitted and new_key and new_name:
        session.add(Group(
            key=new_key,
            name=new_name,
            webhook_footer=new_footer,
            color=new_color,
            webhook_footer_img=new_img,
            webhook_url=new_url,
            enabled=True
        ))
        session.commit()
        st.rerun()

# st.write(f"Loaded groups: {groups}")  # This line shows whether any data is fetched


# .venv\Scripts\Activate
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# streamlit run app.py
