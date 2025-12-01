# pages/1_Group_Service_Matrix.py
import streamlit as st
import pandas as pd
from sqlalchemy.orm import joinedload  # <--- IMPORTANT IMPORT
from db import SessionLocal
# We don't need init_db here; Home.py handles table creation.
from models import GroupService

st.set_page_config(page_title="Group–Service Matrix", layout="wide")

st.title("Group–Service Matrix")

# 1. Open Session
session = SessionLocal()

try:
    # 2. Optimized Query (Eager Load)
    # This fetches the Link, the Group Name, and the Service Name in ONE request.
    results = (
        session.query(GroupService)
        .options(
            joinedload(GroupService.group),
            joinedload(GroupService.service)
        )
        .all()
    )

    # 3. Process Data
    rows = []
    for gs in results:
        rows.append({
            "Group": gs.group.name,
            "Service": gs.service.name,
            "Enabled": gs.enabled,
            "Health": gs.health_status or "unknown",
            "Code": gs.health_code,
            "Last checked": gs.health_checked_at,
            "Webhook URL": gs.webhook_url or "",
        })

    df = pd.DataFrame(rows)

    st.markdown("### Group–Service matrix")

    # Handle case where DB is empty
    if df.empty:
        st.info("No links found.")
    else:
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            group_filter = st.multiselect(
                "Filter by group",
                options=sorted(df["Group"].unique()),
            )
        with col2:
            service_filter = st.multiselect(
                "Filter by service",
                options=sorted(df["Service"].unique()),
            )

        # Apply Filters
        filtered = df.copy()
        if group_filter:
            filtered = filtered[filtered["Group"].isin(group_filter)]
        if service_filter:
            filtered = filtered[filtered["Service"].isin(service_filter)]

        # Display
        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True,
        )

finally:
    # 4. Cleanup
    session.close()