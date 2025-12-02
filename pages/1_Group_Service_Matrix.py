# pages/1_Group_Service_Matrix.py
import streamlit as st
import pandas as pd
from sqlalchemy.orm import joinedload  # <--- IMPORTANT IMPORT
from db import SessionLocal
# We don't need init_db here; Home.py handles table creation.
from models import GroupService
import plotly

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
        group_display_name = gs.group.name
        if gs.group.caption:
            group_display_name += f" | {gs.group.caption.strip()}"
        
        rows.append({
            "Group": group_display_name,
            "Service": gs.service.name,
            "Enabled": gs.enabled,
            "Health": gs.health_status or "unknown",
            "Code": gs.health_code,
            "Last checked": gs.health_checked_at,
            "Webhook URL": gs.webhook_url or "",
        })

    df = pd.DataFrame(rows)

    st.markdown("### Group–Service matrix")

    if df.empty:
        st.info("No links found.")
    else:
        # Create Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Heatmap Matrix", "🔢 Emoji Grid", "📋 Raw List"])

        # --- VISUAL 1: INTERACTIVE HEATMAP (The "Cool" one) ---
        with tab1:
            st.markdown("### Service Coverage Heatmap")
            st.caption("Green = Enabled, Red = Disabled, Grey = Not Linked")

            import plotly.express as px

            # 1. Pivot the data: Index=Group, Col=Service, Value=Enabled
            # We assume 1 = Enabled, 0 = Disabled.
            # If a link is missing entirely in the DB, it will be NaN.
            matrix = df.pivot_table(index="Group", columns="Service", values="Enabled", aggfunc="first")

            # 2. Convert to numeric for coloring (1=True, 0=False)
            # We fill NaN (missing links) with -1 so we can color them differently
            matrix_numeric = matrix.fillna(-1).astype(int)

            # 3. Create Custom Colorscale
            # -1 (Missing) -> Grey
            # 0  (Disabled) -> Red
            # 1  (Enabled)  -> Green
            colors = [
                [0.0, "lightgrey"],  # -1 value
                [0.33, "lightgrey"],
                [0.33, "#fee2e2"],  # 0 value (Light Red)
                [0.66, "#fee2e2"],
                [0.66, "#22c55e"],  # 1 value (Green)
                [1.0, "#22c55e"],
            ]

            # 4. Generate Plot
            fig = px.imshow(
                matrix_numeric,
                color_continuous_scale=colors,
                aspect="auto",  # Adjusts squares to fit width
                labels=dict(x="Service", y="Group", color="Status"),
            )

            # 5. Polish the look
            fig.update_traces(
                xgap=1, ygap=1,  # Add grid lines
                hovertemplate="<b>%{y}</b><br>Service: %{x}<br>Status: %{z}<extra></extra>"
            )
            # Hide the color bar numbers since they are internal logic (-1, 0, 1)
            fig.update_layout(
                coloraxis_showscale=False,
                height=800,
                xaxis_side="top",  # <--- This moves labels to the top
                xaxis_title=None,  # Optional: Removes the word "Service" since the names are obvious
            )

            st.plotly_chart(fig, use_container_width=True)

        # --- VISUAL 2: THE EMOJI GRID (Clean & Readable) ---
        with tab2:
            st.markdown("### Quick Status Grid")

            # Pivot the dataframe to a grid
            emoji_df = df.pivot_table(index="Group", columns="Service", values="Enabled", aggfunc="first")


            # Map True/False to Emojis
            # NaN means the link doesn't exist in the DB
            def status_to_emoji(val):
                if pd.isna(val):
                    return "—"  # or "⚪" for empty
                return "✅" if val else "❌"


            display_df = emoji_df.applymap(status_to_emoji)

            st.dataframe(display_df, use_container_width=True)

        # --- VISUAL 3: ORIGINAL LIST (With your existing filters) ---
        with tab3:
            st.markdown("### Detailed List View")

            # Your original Filter Logic
            col1, col2 = st.columns(2)
            with col1:
                group_filter = st.multiselect("Filter by group", options=sorted(df["Group"].unique()))
            with col2:
                service_filter = st.multiselect("Filter by service", options=sorted(df["Service"].unique()))

            filtered = df.copy()
            if group_filter:
                filtered = filtered[filtered["Group"].isin(group_filter)]
            if service_filter:
                filtered = filtered[filtered["Service"].isin(service_filter)]

            st.dataframe(
                filtered,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Enabled": st.column_config.CheckboxColumn(
                        "Enabled",
                        help="Is this service active?",
                        disabled=True,  # Read-only
                    ),
                    "Webhook URL": st.column_config.TextColumn("Webhook", width="small"),
                }
            )

finally:
    # 4. Cleanup
    session.close()