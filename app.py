import streamlit as st
import sqlite3
import pandas as pd
import os

# --- DATABASE UTILITIES ---
def get_db_connection():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'books.db')
    return sqlite3.connect(db_path)

def run_query(query, params=()):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

# --- APP LAYOUT ---
st.set_page_config(page_title="My Book Collection", layout="wide")
st.title("📚 Personal Library Manager")

tab1, tab2 = st.tabs(["📖 View Collection", "➕ Add/Edit Books"])

# --- TAB 1: VIEWING (Your existing logic) ---
with tab1:

    # Page configuration
    st.set_page_config(page_title="My Book Collection", layout="wide")
    
    
    def load_data():
        # Get the absolute path to the directory this script is in
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'books.db')
        
        conn = sqlite3.connect(db_path)
        # We use a JOIN to show the actual Author Name instead of just the ID number
        query = """
        SELECT 
            B.TITLE, 
            B.SUMMARY, 
            B.ISBN, 
            B.CATEGORIES,
            B.PUBLISHED_DATE,
            A.LASTNAME as AUTHOR_NAME,
            L.NAME as LANGUAGE,
            O.name as OWNER,
            S.name as STATUS
        FROM BOOK B
        LEFT JOIN AUTHOR A ON B.AUTHOR = A.ID
        LEFT JOIN LANGUAGES L ON B.LANGUAGE_ID = L.ID
        LEFT JOIN OWNER O ON B.OWNER_id = O.id
        LEFT JOIN STATUS S ON B.STATUS_ID = S.id
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    st.title("📚 Personal Library Manager")
    
    # Load the data
    df = load_data()
    
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filters")
    search_term = st.sidebar.text_input("Search Title or Summary")
    selected_category = st.sidebar.selectbox("Category", ["Alle"] + list(df['CATEGORIES'].unique()))
    selected_language = st.sidebar.selectbox("Language", ["Alle"] + list(df['LANGUAGE'].unique()))
    selected_owner = st.sidebar.selectbox("In Besitz?", ["Alle"] + list(df['OWNER'].unique()))
    selected_status = st.sidebar.selectbox("Lesestatus", ["Alle"] + list(df['STATUS'].unique()))
    
    # --- FILTER LOGIC ---
    filtered_df = df.copy()
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['TITLE'].str.contains(search_term, case=False, na=False) | 
            filtered_df['SUMMARY'].str.contains(search_term, case=False, na=False)
        ]
    
    if selected_category != "Alle":
        filtered_df = filtered_df[filtered_df['CATEGORIES'] == selected_category]
        
    if selected_language != "Alle":
        filtered_df = filtered_df[filtered_df['LANGUAGE'] == selected_language]
    
    if selected_owner != "Alle":
        filtered_df = filtered_df[filtered_df['OWNER'] == selected_owner]
    
    if selected_status != "Alle":
        filtered_df = filtered_df[filtered_df['STATUS'] == selected_status]
    
    # --- DISPLAY ---
    st.write(f"Zeigt {len(filtered_df)} Einträge")
    
    # Display as a clean table or cards
    for index, row in filtered_df.iterrows():
        with st.container():
            st.subheader(row['TITLE'])
            st.write(f"**Author:** {row['AUTHOR_NAME']} | **Kategorie:** {row['CATEGORIES']} | **Sprache:** {row['LANGUAGE']} | **Status:** {row['OWNER']}, {row['STATUS']}")
            with st.expander("Zusammenfassung ausklappen"):
                st.write(row['SUMMARY'])
            st.divider()


    # ... (Your existing load_data and filter code goes here)
    pass

# --- TAB 2: ADD/EDIT ENTRIES ---
with tab2:
    st.header("Manage Entries")
    
    # We need to fetch current lists for dropdowns
    conn = get_db_connection()
    authors = pd.read_sql_query("SELECT id, lastname FROM AUTHOR", conn)
    statuses = pd.read_sql_query("SELECT id, name FROM STATUS", conn)
    owners = pd.read_sql_query("SELECT id, name FROM OWNER", conn)
    languages = pd.read_sql_query("SELECT id, name FROM LANGUAGES", conn)
    conn.close()

    with st.form("add_book_form"):
        st.subheader("Add New Book")
        new_title = st.text_input("Title")
        new_summary = st.text_area("Summary")
        new_isbn = st.text_input("ISBN")
        
        # Dropdowns using the IDs from the DB
        author_choice = st.selectbox("Author", authors['lastname'].tolist())
        status_choice = st.selectbox("Status", statuses['name'].tolist())
        owner_choice = st.selectbox("Owner", owners['name'].tolist())
        lang_choice = st.selectbox("Language", languages['name'].tolist())
        
        submit_button = st.form_submit_button("Save Book")

        if submit_button:
            # Map names back to IDs
            a_id = authors[authors['lastname'] == author_choice]['id'].values[0]
            s_id = statuses[statuses['name'] == status_choice]['id'].values[0]
            o_id = owners[owners['name'] == owner_choice]['id'].values[0]
            l_id = languages[languages['name'] == lang_choice]['id'].values[0]

            insert_query = """
            INSERT INTO BOOK (TITLE, SUMMARY, ISBN, AUTHOR, STATUS_ID, OWNER_ID, LANGUAGE_ID)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            run_query(insert_query, (new_title, new_summary, new_isbn, int(a_id), int(s_id), int(o_id), int(l_id)))
            st.success(f"Added '{new_title}' successfully!")
            st.rerun() # Refresh to show new data in Tab 1
