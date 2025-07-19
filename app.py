import streamlit as st
import pandas as pd
import googlemaps
import pathlib
import datetime
import os
import uuid
import hashlib
import csv

# Setup page
st.set_page_config(page_title="Toddler Activities", layout="wide")

USER_FILE = "users.csv"
SAVED_FILE = "saved_activities.csv"


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to register a new user
def register_user(username, password):
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['userID', 'username', 'password'])

    # Check if username exists
    with open(USER_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['username'] == username:
                return False  # Username exists

    user_id = str(uuid.uuid4())
    with open(USER_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([user_id, username, hash_password(password)])
    return True

# Function to authenticate a user
def authenticate_user(username, password):
    if not os.path.exists(USER_FILE):
        return False
    hashed_input = hash_password(password)
    with open(USER_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['username'] == username and row['password'] == hashed_input:
                return row['userID'] 
    return False

# Load CSS
def load_css(file_path):
    if file_path.exists():
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("CSS file not found!")

css_path = pathlib.Path("style.css")
load_css(css_path)


# Initialize state
if "page" not in st.session_state:
    st.session_state.page = "search"
if "comments" not in st.session_state:
    st.session_state.comments = {}
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

# Session state for login
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "login_page" not in st.session_state:
    st.session_state.login_page = "login"  # or "register"

# Load data
df = pd.read_csv("data.csv")

# Setup Google Maps
API_key = "AIzaSyB2fDGZPEJvhoHolrAbbR-pz3mvpl_v6_E"
gmaps = googlemaps.Client(key=API_key)

# Functions
def get_lat_long(address):
    try:
        geocode_result = gmaps.geocode(address)
        if geocode_result:
            lat = geocode_result[0]['geometry']['location']['lat']
            lng = geocode_result[0]['geometry']['location']['lng']
            return lat, lng
    except Exception as e:
        st.error(f"Error: {e}")
    return None, None

def get_coordinates(row):
    if pd.notna(row.get('Latitude')) and pd.notna(row.get('Longitude')):
        return pd.Series([row['Latitude'], row['Longitude']])
    return pd.Series(get_lat_long(row['Postcode']))

df[['Latitude', 'Longitude']] = df.apply(get_coordinates, axis=1)
df.to_csv("data.csv", index=False)

def get_gmaps_distance(user_lat, user_lng, dest_lat, dest_lng):
    try:
        origin = (user_lat, user_lng)
        destination = (dest_lat, dest_lng)
        result = gmaps.distance_matrix(origin, destination, mode='walking')
        status = result['rows'][0]['elements'][0]['status']
        if status == "OK":
            meters = result['rows'][0]['elements'][0]['distance']['value']
            return round(meters / 1609.34, 2)  # Convert to miles
    except Exception as e:
        st.error(f"Distance error: {e}")
    return float("inf")

# --- Authentication Page ---
if not st.session_state.authenticated:
    st.title("🔐 Welcome to Toddler Activities Finder")
    
    st.subheader("Login" if st.session_state.login_page == "login" else "Register")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.session_state.login_page == "login":
        if st.button("Login"):
            user_id = authenticate_user(username, password)
            if user_id:
                st.success("Login successful!")
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_id = user_id  # ✅ store userID
                st.rerun()
            else:
                st.error("Invalid username or password.")
        if st.button("Need an account? Register here"):
            st.session_state.login_page = "register"
            st.rerun()
    else:  # registration
        if st.button("Register"):
            if register_user(username, password):
                st.success("Registration successful! You can now log in.")
                st.session_state.login_page = "login"
            else:
                st.warning("Username already exists.")
        if st.button("Back to Login"):
            st.session_state.login_page = "login"
            st.rerun()
    st.stop()

# --- Sidebar for authenticated users ---
with st.sidebar:
    st.markdown("<div style='text-align:center; margin-top: 20px;'>", unsafe_allow_html=True)
    if st.button("👤 My Profile"):
        st.session_state.page = "profile"
        st.rerun()
    if st.button("🔍 Search Activities"):
        st.session_state.page = "search"
        st.rerun()
    if st.button("🚪 Logout", key="logout_button"):
        st.session_state.authenticated = False
        st.session_state.login_page = "login"
        st.session_state.username = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
  


# --- Search Page ---
if st.session_state.page == "search":
    st.markdown(
        """
        <h1 style="animation: bounce 2s infinite; text-align:center;">
            🌈 Find local activities for toddlers
        </h1>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown("<div style='background:#fffde7; padding:20px; border-radius:20px; box-shadow:0 4px 15px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([3, 2, 2])
        user_input = col1.text_input("Please enter your postcode", key="styledinput")
        user_input_distance = col2.number_input("Distance in miles", min_value=0, max_value=100, value=1, step=1, key="styledinput2")
        user_input_day = col3.multiselect("Which day?", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="styledinput3")

        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Search"):
        if not user_input or not user_input_day:
            st.warning("Please fill in all fields.")
        else:
            user_lat, user_lng = get_lat_long(user_input)

            df[['Latitude', 'Longitude']] = df.apply(get_coordinates, axis=1)

            # Optional: save updated coords for future use
            df.to_csv("data.csv", index=False)

            df["distance"] = df.apply(
                lambda row: get_gmaps_distance(user_lat, user_lng, row["Latitude"], row["Longitude"]),
                axis=1
            )

            results = df[(df['distance'] <= user_input_distance) & (df['Day'].isin(user_input_day))]
            st.session_state.results = results
            st.session_state.page = "view"
            st.rerun()

# --- View Page ---
elif st.session_state.page == "view":
    
    res = st.session_state.results
    st.title("🎯 Matching Toddler Activities")

    if res.empty:
        st.warning("No results found.")
    else:
        for idx, i in enumerate(res[['ActivityID','Title','Place','Day','Time', 'Description', 'Address', 'Postcode', 'Contact', 'Age', 'Booking', 'Price']].values):
            activity_id = i[0]
            activity_key = f"{activity_id}_{i[1]}"  # Optional: still use this for internal comment dict

            with st.container():
                st.markdown(f"""
                    <div style="
                        border: 2px solid #90caf9;
                        background-color: #f1faff;
                        padding: 20px;
                        border-radius: 15px;
                        margin-bottom: 20px;
                    ">
                        <h3 style="color:#1976d2;">🧸 {i[1]} at {i[2]}</h3>
                        <p><strong>When:</strong> {i[3]} at {i[4]}</p>
                        <p><strong>Description:</strong> {i[5]}</p>
                        <p><strong>Where:</strong> {i[6]}, {i[7]}</p>
                        <p><strong>Contact:</strong> {i[8]} &nbsp; | &nbsp;
                            <strong>Age:</strong> {i[9]} &nbsp; | &nbsp;
                            <strong>Booking:</strong> {i[10]} &nbsp; | &nbsp;
                            <strong>Price:</strong> {i[11]}
                        </p>
                    </div>
            """, unsafe_allow_html=True)
                # Load saved activities
                if os.path.exists(SAVED_FILE):
                    saved_df = pd.read_csv(SAVED_FILE)
                else:
                    saved_df = pd.DataFrame(columns=["UserID", "ActivityID", "Timestamp"])

                is_saved = not saved_df[
                    (saved_df["UserID"] == st.session_state.user_id) & 
                    (saved_df["ActivityID"] == activity_id)
                ].empty

                save_label = "❤️ Saved" if is_saved else "🤍 Save"
                if st.button(save_label, key=f"save_{idx}"):
                    if is_saved:
                        saved_df = saved_df[
                            ~((saved_df["UserID"] == st.session_state.user_id) & (saved_df["ActivityID"] == activity_id))
                        ]
                        st.success("Removed from saved activities.")
                    else:
                        new_row = pd.DataFrame([{
                            "UserID": st.session_state.user_id,
                            "ActivityID": activity_id,
                            "Timestamp": datetime.datetime.now().isoformat()
                        }])
                        saved_df = pd.concat([saved_df, new_row], ignore_index=True)
                        st.success("Activity saved!")

                    saved_df.to_csv(SAVED_FILE, index=False)
                    st.rerun()

        
                # Show recent comments before input
                if os.path.exists("comments.csv"):
                    full_comments = pd.read_csv("comments.csv", dtype=str)
                    matching_comments = full_comments[full_comments["ActivityID"] == activity_id].sort_values(by="Timestamp", ascending=False).head(5)

                    if not matching_comments.empty:
                        st.markdown("""
                        <div style="
                            background-color: #e3f2fd; 
                            border: 1px solid #90caf9;
                            border-radius: 12px; 
                            padding: 16px; 
                            margin-top: 10px;
                            margin-bottom: 16px;
                        ">
                        <strong>💬 Recent Comments:</strong>
                        """, unsafe_allow_html=True)
                        for jdx, row in matching_comments.iterrows():
                            col1, col2 = st.columns([5, 1])
                            col1.markdown(f"- *{row['Timestamp']}* — {row['Comment']}")

                            if row["UserID"] == st.session_state.user_id:
                                if col2.button("🗑️", key=f"delete_{idx}_{jdx}"):
                                    full_comments = full_comments[
                                        ~(
                                            (full_comments["UserID"] == row["UserID"]) &
                                            (full_comments["ActivityID"] == row["ActivityID"]) &
                                            (full_comments["Title"] == row["Title"]) &
                                            (full_comments["Comment"] == row["Comment"]) &
                                            (full_comments["Timestamp"] == row["Timestamp"])
                                        )
                                    ]
                                    full_comments.to_csv("comments.csv", index=False)
                                    st.success("Comment deleted.")
                                    st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                # Now show comment input
                comment = st.text_input(f"Leave a comment:", key=f"comment_input_{idx}")
                if st.button("Submit Comment", key=f"submit_comment_{idx}"):
                    if comment:
                        if activity_key not in st.session_state.comments:
                            st.session_state.comments[activity_key] = []
                        st.session_state.comments[activity_key].append(comment)

                        comment_data = {
                            "UserID": st.session_state.user_id,
                            "ActivityID": activity_id,
                            "Title": i[1],  # i[1] is the activity title from earlier in your loop
                            "Comment": comment,
                            "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d")
                        }

                        comment_df = pd.DataFrame([comment_data])
                        file_exists = os.path.isfile("comments.csv")
                        comment_df.to_csv("comments.csv", mode='a', header=not file_exists, index=False)
                        st.success(f"Comment saved and submitted for {i[1]}!")
                    else:
                        st.warning("Please enter a comment before submitting.")
                    
    st.markdown("---")
    if st.button("🔙 Back to Search", key="back_to_search_from_view"):
        st.session_state.page = "search"
        st.rerun()



elif st.session_state.page == "profile":
    st.title("👤 Your Profile")
    st.markdown(f"""
        <div style='font-size: 1.1rem; margin-bottom: 20px; color: #444;'>
            Logged in as <strong>{st.session_state.username}</strong>
        </div>
    """, unsafe_allow_html=True)


    # Load saved activities
    if os.path.exists(SAVED_FILE):
        saved_df = pd.read_csv(SAVED_FILE)
        user_saves = saved_df[saved_df["UserID"] == st.session_state.user_id]
    else:
        user_saves = pd.DataFrame()

    st.markdown("### ❤️ Saved Activities")
    if user_saves.empty:
        st.info("You haven’t saved any activities yet.")
    else:
        saved_ids = user_saves["ActivityID"].tolist()
        saved_activities = df[df["ActivityID"].isin(saved_ids)]

        for idx, i in saved_activities.iterrows():
            st.markdown(f"""
                <div style="border:1px solid #ccc; padding:15px; border-radius:12px; margin-bottom:15px;">
                    <h4>🧸 {i['Title']} at {i['Place']}</h4>
                    <p><strong>Day:</strong> {i['Day']} at {i['Time']}</p>
                    <p><strong>Postcode:</strong> {i['Postcode']}</p>
                    <p><strong>Description:</strong> {i['Description']}</p>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🗑️ Remove from Saved", key=f"remove_{idx}"):
                saved_df = saved_df[
                    ~((saved_df["UserID"] == st.session_state.user_id) & (saved_df["ActivityID"] == i["ActivityID"]))
                ]
                saved_df.to_csv(SAVED_FILE, index=False)
                st.success("Removed from saved.")
                st.rerun()

    st.markdown("### 💬 Your Recent Comments")

    if os.path.exists("comments.csv"):
        comments = pd.read_csv("comments.csv", dtype=str)
        user_comments = comments[comments["UserID"] == st.session_state.user_id]

        if not user_comments.empty:
            for idx, row in user_comments.sort_values(by="Timestamp", ascending=False).head(10).iterrows():
                st.markdown(f"""
                    <div style="border:1px solid #ccc; padding:10px; border-radius:10px; margin-bottom:10px;">
                        <strong>{row['Timestamp']}</strong> — {row['Comment']}<br/>
                        <small>Activity: {row['Title']}</small>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_com_{idx}"):
                    comments = comments[
                        ~(
                            (comments["UserID"] == row["UserID"]) &
                            (comments["ActivityID"] == row["ActivityID"]) &
                            (comments["Title"] == row["Title"]) &
                            (comments["Comment"] == row["Comment"]) &
                            (comments["Timestamp"] == row["Timestamp"])
                        )
                    ]
                    comments.to_csv("comments.csv", index=False)
                    st.success("Comment deleted.")
                    st.rerun()
        else:
            st.info("You haven't made any comments yet.")
    else:
        st.info("No comments found.")

    st.markdown("---")
    if st.button("❌ Delete My Account"):
        st.warning("This will permanently delete your account and all your data.")
        if st.button("⚠️ Confirm Delete Account"):
            # Delete user from users.csv
            users = pd.read_csv(USER_FILE)
            users = users[users["userID"] != st.session_state.user_id]
            users.to_csv(USER_FILE, index=False)

            # Delete saved activities
            if os.path.exists(SAVED_FILE):
                saved_df = pd.read_csv(SAVED_FILE)
                saved_df = saved_df[saved_df["UserID"] != st.session_state.user_id]
                saved_df.to_csv(SAVED_FILE, index=False)

            # Delete comments
            if os.path.exists("comments.csv"):
                comments = pd.read_csv("comments.csv")
                comments = comments[comments["UserID"] != st.session_state.user_id]
                comments.to_csv("comments.csv", index=False)

            # Clear session
            st.session_state.authenticated = False
            st.session_state.username = None
            st.success("Account and data deleted.")
            st.rerun()




    st.markdown("---")
    if st.button("🔙 Back to Search"):
        st.session_state.page = "search"
        st.rerun()


