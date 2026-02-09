import os
from datetime import datetime, date, time as dt_time

import altair as alt
import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def api_request(method: str, path: str, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API_BASE_URL}{path}"
    return requests.request(method, url, headers=headers, timeout=20, **kwargs)


@st.cache_data(show_spinner=False)
def fetch_me(token: str):
    r = api_request("GET", "/me", token=token)
    return r.json() if r.status_code == 200 else None


@st.cache_data(show_spinner=False)
def fetch_leads(token: str):
    r = api_request("GET", "/leads", token=token)
    return r.json() if r.status_code == 200 else []


@st.cache_data(show_spinner=False)
def fetch_notes(token: str, lead_id: int):
    r = api_request("GET", f"/leads/{lead_id}/notes", token=token)
    return r.json() if r.status_code == 200 else []


@st.cache_data(show_spinner=False)
def fetch_meetings(token: str):
    r = api_request("GET", "/meetings", token=token)
    return r.json() if r.status_code == 200 else []


@st.cache_data(show_spinner=False)
def fetch_users(token: str):
    r = api_request("GET", "/users", token=token)
    return r.json() if r.status_code == 200 else []


def clear_cache():
    st.cache_data.clear()


def leads_df(leads: list[dict]) -> pd.DataFrame:
    if not leads:
        return pd.DataFrame()
    df = pd.DataFrame(leads)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    if "last_email_sent_at" in df.columns:
        df["last_email_sent_at"] = pd.to_datetime(df["last_email_sent_at"], errors="coerce")
    return df


def meetings_df(meetings: list[dict]) -> pd.DataFrame:
    if not meetings:
        return pd.DataFrame()
    df = pd.DataFrame(meetings)
    if "scheduled_time" in df.columns:
        df["scheduled_time"] = pd.to_datetime(df["scheduled_time"], errors="coerce")
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df


st.set_page_config(page_title="Sales CRM", layout="wide")

if "token" not in st.session_state:
    st.session_state.token = None
if "me" not in st.session_state:
    st.session_state.me = None

st.title("Sales CRM UI")

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Go to",
        ["Dashboard", "Leads", "Meetings", "Users", "Auth"],
    )

    st.divider()
    st.subheader("Session")
    if st.session_state.token:
        st.success("Logged in")
        if st.session_state.me:
            st.caption(
                f"{st.session_state.me.get('name', '')} | "
                f"{st.session_state.me.get('role', '')}"
            )
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.me = None
            clear_cache()
            st.rerun()
    else:
        st.info("Not logged in")

    st.divider()
    if st.session_state.token and st.button("Refresh Data"):
        clear_cache()
        st.rerun()


if page in ["Dashboard", "Leads", "Meetings", "Users"] and not st.session_state.token:
    st.warning("Please login first.")
    st.stop()


if page == "Dashboard":
    st.subheader("Overview")

    leads = fetch_leads(st.session_state.token)
    meetings = fetch_meetings(st.session_state.token)

    ldf = leads_df(leads)
    mdf = meetings_df(meetings)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Leads", len(ldf))
    col2.metric("Meetings", len(mdf))
    if not ldf.empty and "status" in ldf.columns:
        col3.metric("Contacted", int((ldf["status"] == "contacted").sum()))
        col4.metric("Qualified", int((ldf["status"] == "qualified").sum()))
    else:
        col3.metric("Contacted", 0)
        col4.metric("Qualified", 0)

    st.divider()

    if not ldf.empty:
        st.markdown("Lead Status Distribution")
        status_counts = ldf["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        chart = (
            alt.Chart(status_counts)
            .mark_bar()
            .encode(x="status", y="count")
        )
        st.altair_chart(chart, use_container_width=True)

        if "budget" in ldf.columns:
            st.markdown("Lead Budget Distribution")
            budget_df = ldf.copy()
            budget_df["budget"] = budget_df["budget"].fillna(0)
            chart2 = (
                alt.Chart(budget_df)
                .mark_bar()
                .encode(x=alt.X("budget:Q", bin=alt.Bin(maxbins=12)), y="count()")
            )
            st.altair_chart(chart2, use_container_width=True)

        if "created_at" in ldf.columns:
            st.markdown("Leads Over Time")
            time_df = ldf.dropna(subset=["created_at"]).copy()
            if not time_df.empty:
                time_df["day"] = time_df["created_at"].dt.date
                daily = time_df.groupby("day").size().reset_index(name="count")
                chart3 = (
                    alt.Chart(daily)
                    .mark_line(point=True)
                    .encode(x="day:T", y="count:Q")
                )
                st.altair_chart(chart3, use_container_width=True)


if page == "Leads":
    st.subheader("Leads")

    leads = fetch_leads(st.session_state.token)
    ldf = leads_df(leads)

    with st.sidebar:
        st.subheader("Lead Filters")
        search = st.text_input("Search name/email")
        status_filter = st.multiselect(
            "Status",
            ["new", "contacted", "qualified", "closed"],
        )
        budget_min, budget_max = st.slider(
            "Budget range",
            min_value=0,
            max_value=50000,
            value=(0, 50000),
            step=500,
        )

    if not ldf.empty:
        if search:
            ldf = ldf[
                ldf["name"].str.contains(search, case=False, na=False)
                | ldf["email"].str.contains(search, case=False, na=False)
            ]
        if status_filter:
            ldf = ldf[ldf["status"].isin(status_filter)]
        if "budget" in ldf.columns:
            ldf["budget"] = ldf["budget"].fillna(0)
            ldf = ldf[(ldf["budget"] >= budget_min) & (ldf["budget"] <= budget_max)]

    left, right = st.columns([1.2, 1.8], gap="large")

    with left:
        st.markdown("Lead List")
        if ldf.empty:
            st.info("No leads found.")
        else:
            display_cols = [
                c for c in ["id", "name", "email", "status", "budget", "assigned_to", "created_at"]
                if c in ldf.columns
            ]
            st.dataframe(ldf[display_cols], use_container_width=True)

        with st.expander("Create Lead", expanded=False):
            with st.form("create_lead_form"):
                name = st.text_input("Name")
                email = st.text_input("Email (optional)")
                phone = st.text_input("Phone (optional)")
                service_type = st.text_input("Service Type", value="AI services")
                budget = st.number_input("Budget", min_value=0, value=0, step=500)
                submitted = st.form_submit_button("Create Lead")

            if submitted:
                payload = {
                    "name": name,
                    "email": email or None,
                    "phone": phone or None,
                    "service_type": service_type,
                    "budget": budget or None,
                }
                r = api_request("POST", "/leads", token=st.session_state.token, json=payload)
                if r.status_code == 201:
                    st.success("Lead created.")
                    clear_cache()
                    st.rerun()
                else:
                    st.error(r.text)

    with right:
        st.markdown("Lead Detail")
        if ldf.empty:
            st.info("Select a lead to view details.")
        else:
            lead_options = ldf["id"].tolist()
            selected_id = st.selectbox("Lead ID", lead_options)
            lead_row = ldf[ldf["id"] == selected_id].iloc[0]

            st.write(
                {
                    "name": lead_row.get("name"),
                    "email": lead_row.get("email"),
                    "phone": lead_row.get("phone"),
                    "status": lead_row.get("status"),
                    "budget": lead_row.get("budget"),
                    "service_type": lead_row.get("service_type"),
                    "assigned_to": lead_row.get("assigned_to"),
                    "created_at": str(lead_row.get("created_at")),
                }
            )

            st.divider()
            st.markdown("Conversation Notes")
            notes = fetch_notes(st.session_state.token, int(selected_id))
            if notes:
                ndf = pd.DataFrame(notes)
                st.dataframe(ndf, use_container_width=True)
            else:
                st.info("No notes yet.")

            with st.form("add_note_form"):
                note = st.text_area("Note")
                sender = st.selectbox("Sender", ["sales", "lead"])
                submitted = st.form_submit_button("Add Note")

            if submitted:
                payload = {"note": note, "sender": sender}
                r = api_request(
                    "POST",
                    f"/leads/{int(selected_id)}/notes",
                    token=st.session_state.token,
                    json=payload,
                )
                if r.status_code == 201:
                    data = r.json()
                    st.success("Note saved.")
                    if data.get("ai_response"):
                        st.info(f"AI Response: {data['ai_response']}")
                    clear_cache()
                    st.rerun()
                else:
                    st.error(r.text)


if page == "Meetings":
    st.subheader("Meetings")

    meetings = fetch_meetings(st.session_state.token)
    mdf = meetings_df(meetings)

    left, right = st.columns([1.2, 1.8], gap="large")

    with left:
        st.markdown("Schedule Meeting")
        with st.form("create_meeting_form"):
            lead_id = st.number_input("Lead ID", min_value=1, value=1, step=1)
            meet_date = st.date_input("Date", value=date.today())
            meet_time = st.time_input("Time", value=dt_time(10, 0))
            submitted = st.form_submit_button("Schedule")

        if submitted:
            scheduled = datetime.combine(meet_date, meet_time).isoformat()
            payload = {"lead_id": int(lead_id), "scheduled_time": scheduled}
            r = api_request("POST", "/meetings", token=st.session_state.token, json=payload)
            if r.status_code == 201:
                st.success("Meeting scheduled.")
                clear_cache()
                st.rerun()
            else:
                st.error(r.text)

        st.divider()
        st.markdown("Update Meeting Status")
        if not mdf.empty:
            with st.form("update_meeting_form"):
                meeting_id = st.selectbox("Meeting ID", mdf["id"].tolist())
                status = st.selectbox("Status", ["scheduled", "complete", "cancelled"])
                submitted = st.form_submit_button("Update")

            if submitted:
                payload = {"status": status}
                r = api_request(
                    "PUT",
                    f"/meetings/{int(meeting_id)}",
                    token=st.session_state.token,
                    json=payload,
                )
                if r.status_code == 200:
                    st.success("Meeting updated.")
                    clear_cache()
                    st.rerun()
                else:
                    st.error(r.text)
        else:
            st.info("No meetings to update.")

    with right:
        st.markdown("Meeting List")
        if mdf.empty:
            st.info("No meetings found.")
        else:
            display_cols = [
                c for c in ["id", "lead_id", "manager_id", "scheduled_time", "status", "created_at"]
                if c in mdf.columns
            ]
            st.dataframe(mdf[display_cols], use_container_width=True)


if page == "Users":
    st.subheader("Users (Admin Only)")
    users = fetch_users(st.session_state.token)
    if users:
        udf = pd.DataFrame(users)
        st.dataframe(udf, use_container_width=True)
    else:
        st.info("No users found or not authorized.")


if page == "Auth":
    st.subheader("Authentication")

    tab_register, tab_verify, tab_login = st.tabs(["Register", "Verify OTP", "Login"])

    with tab_register:
        with st.form("register_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["admin", "sales", "meeting_manager"])
            submitted = st.form_submit_button("Register")

        if submitted:
            payload = {"name": name, "email": email, "password": password, "role": role}
            r = api_request("POST", "/register", json=payload)
            if r.status_code == 201:
                st.success("Registered. Check your email for OTP.")
            else:
                st.error(r.text)

    with tab_verify:
        with st.form("verify_form"):
            email = st.text_input("Email", key="verify_email")
            otp = st.text_input("OTP", key="verify_otp")
            submitted = st.form_submit_button("Verify OTP")

        if submitted:
            payload = {"email": email, "otp": otp}
            r = api_request("POST", "/verify-otp", json=payload)
            if r.status_code == 200:
                st.success("Verified successfully.")
            else:
                st.error(r.text)

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pw")
            submitted = st.form_submit_button("Login")

        if submitted:
            payload = {"email": email, "password": password}
            r = api_request("POST", "/login", json=payload)
            if r.status_code == 200:
                data = r.json()
                st.session_state.token = data["access_token"]
                st.session_state.me = fetch_me(st.session_state.token)
                st.success("Logged in.")
                st.rerun()
            else:
                st.error(r.text)
