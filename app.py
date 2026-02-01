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
    
    # --- DATA PREPARATION ---
    conn = get_db_connection()
    
    # Authors with combined name and sorting
    authors = pd.read_sql_query("SELECT ID, FIRSTNAME, LASTNAME FROM AUTHOR", conn)
    authors.columns = [c.upper() for c in authors.columns]
    authors['FULL_NAME'] = authors['LASTNAME'] + ", " + authors['FIRSTNAME']
    author_list = sorted(authors['FULL_NAME'].tolist())
    
    # Get other tables
    statuses = pd.read_sql_query("SELECT * FROM STATUS", conn); statuses.columns = [c.upper() for c in statuses.columns]
    owners = pd.read_sql_query("SELECT * FROM OWNER", conn); owners.columns = [c.upper() for c in owners.columns]
    languages = pd.read_sql_query("SELECT * FROM LANGUAGES", conn); languages.columns = [c.upper() for c in languages.columns]
    
    # Get current books for the "Edit" selector
    books_df = pd.read_sql_query("SELECT ID, TITLE FROM BOOK", conn)
    books_df.columns = [c.upper() for c in books_df.columns]
    book_titles = sorted(books_df['TITLE'].tolist())
    
    conn.close()

    # --- EDIT SECTION ---
    st.subheader("📝 Edit Existing Book")
    selected_book_title = st.selectbox("Select a book to edit", ["-- Choose a Book --"] + book_titles)

    if selected_book_title != "-- Choose a Book --":
        # Fetch current details of the selected book
        book_id = books_df[books_df['TITLE'] == selected_book_title]['ID'].values[0]
        
        # We need a fresh connection to get the specific record
        with get_db_connection() as conn:
            current_book = pd.read_sql_query(f"SELECT * FROM BOOK WHERE ID = {book_id}", conn).iloc[0]
        
        with st.form("edit_book_form"):
            # Pre-fill inputs using 'value' or 'index'
            edit_title = st.text_input("Title", value=current_book['TITLE'])
            edit_summary = st.text_area("Summary", value=current_book['SUMMARY'])
            
            # Find the index of the current values to set them as defaults in dropdowns
            # We match IDs to find the correct dropdown position
            def get_index(df, col, current_val):
                try:
                    return df[df[col] == current_val].index[0]
                except:
                    return 0

            edit_author = st.selectbox("Author", author_list, 
                                      index=author_list.index(authors[authors['ID'] == current_book['AUTHOR']]['FULL_NAME'].values[0]))
            
            # ... (Add other selectboxes like status/owner similarly)

            save_changes = st.form_submit_button("Update Book")

            if save_changes:
                # Map selected full name back to ID
                new_a_id = authors[authors['FULL_NAME'] == edit_author]['ID'].values[0]
                
                update_query = """
                UPDATE BOOK 
                SET TITLE = ?, SUMMARY = ?, AUTHOR = ?
                WHERE ID = ?
                """
                run_query(update_query, (edit_title, edit_summary, int(new_a_id), int(book_id)))
                st.success(f"Updated '{edit_title}'!")
                st.rerun()
