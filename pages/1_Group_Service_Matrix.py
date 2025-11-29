# pages/1_Group_Service_Matrix.py
import streamlit as st
import pandas as pd

from db import SessionLocal, init_db
from models import GroupService  # also Group, Service if you need them elsewhere

st.set_page_config(page_title="Group–Service Matrix", layout="wide")

init_db()
session = SessionLocal()

st.title("Group–Service Matrix")

links_df = (
    session.query(GroupService)
    .join(GroupService.group)
    .join(GroupService.service)
    .all()
)

rows_df = []
for gs in links_df:
    rows_df.append({
        "Group": gs.group.name,
        "Service": gs.service.name,
        "Enabled": gs.enabled,
        "Health": gs.health_status or "unknown",
        "Code": gs.health_code,
        "Last checked": gs.health_checked_at,
        "Webhook URL": gs.webhook_url or "",
    })

df = pd.DataFrame(rows_df)

st.markdown("### Group–Service matrix")

col1_df, col2_df = st.columns(2)
with col1_df:
    group_filter_df = st.multiselect(
        "Filter by group",
        options=sorted(df["Group"].unique()),
    )
with col2_df:
    service_filter_df = st.multiselect(
        "Filter by service",
        options=sorted(df["Service"].unique()),
    )

filtered = df.copy()
if group_filter_df:
    filtered = filtered[filtered["Group"].isin(group_filter_df)]
if service_filter_df:
    filtered = filtered[filtered["Service"].isin(service_filter_df)]

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
)

session.close()
