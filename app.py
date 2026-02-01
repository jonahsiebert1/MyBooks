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
    
    conn = get_db_connection()
    # Using 'AS' in SQL ensures we know exactly what the column name will be in Pandas
    authors = pd.read_sql_query("SELECT id, LASTNAME as lastname FROM AUTHOR", conn)
    statuses = pd.read_sql_query("SELECT id, name FROM STATUS", conn)
    owners = pd.read_sql_query("SELECT id, name FROM OWNER", conn)
    languages = pd.read_sql_query("SELECT id, name FROM LANGUAGES", conn)
    conn.close()

    # 1. Start the Form
    with st.form("add_book_form", clear_on_submit=True):
        st.subheader("Add New Book")
        new_title = st.text_input("Title")
        new_summary = st.text_area("Summary")
        new_isbn = st.text_input("ISBN")
        
        # We use .get() or check empty to prevent errors if the DB tables are empty
        author_list = authors['lastname'].tolist() if not authors.empty else ["No Authors Found"]
        status_list = statuses['name'].tolist() if not statuses.empty else ["No Status Found"]
        
        author_choice = st.selectbox("Author", author_list)
        status_choice = st.selectbox("Status", status_list)
        owner_choice = st.selectbox("Owner", owners['name'].tolist())
        lang_choice = st.selectbox("Language", languages['name'].tolist())
        
        # 2. THE SUBMIT BUTTON (Must be inside the 'with st.form' block)
        submitted = st.form_submit_button("Save Book to Database")

        # 3. Handle Form Submission
        if submitted:
            if not new_title:
                st.error("Please enter a Title.")
            else:
                try:
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
                    st.success(f"✅ Added '{new_title}' successfully!")
                    # Use st.rerun() so Tab 1 updates immediately
                    st.rerun()
                except Exception as e:
                    st.error(f"An error occurred: {e}")
