import streamlit as st
import sqlite3
import pandas as pd
import os
from typing import Tuple, List, Dict
from contextlib import contextmanager

# --- CONSTANTS ---
DEFAULT_FILTER_OPTION = "Alle"
DEFAULT_BOOK_SELECT = "-- Choose a Book --"

# --- DATABASE UTILITIES ---
def get_db_connection():
    """Get a connection to the SQLite database."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'books.db')
    return sqlite3.connect(db_path)

def run_query(query: str, params: Tuple = ()) -> None:
    """Execute a query that modifies the database (INSERT, UPDATE, DELETE)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def fetch_query(query: str, params: Tuple = ()) -> pd.DataFrame:
    """Execute a query and return results as a DataFrame."""
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)

# --- DATA LOADING FUNCTIONS ---
@st.cache_data
def load_readings() -> pd.DataFrame:
    """Load all reading sessions from the database."""
    return fetch_query("SELECT * FROM READINGS")

@st.cache_data
def load_books_collection() -> pd.DataFrame:
    """Load the books collection with author and metadata information."""
    query = """
    SELECT 
        B.ID,
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
    return fetch_query(query)

@st.cache_data
def load_authors() -> pd.DataFrame:
    """Load all authors and create a display name."""
    authors = fetch_query("SELECT ID, FIRSTNAME, LASTNAME FROM AUTHOR")
    authors.columns = [c.upper() for c in authors.columns]
    authors['FIRSTNAME'] = authors['FIRSTNAME'].fillna('')
    authors['LASTNAME'] = authors['LASTNAME'].fillna('')
    authors['FULL_NAME'] = (authors['LASTNAME'] + ", " + authors['FIRSTNAME']).str.strip(", ")
    return authors

@st.cache_data
def load_dropdown_data(table_name: str) -> pd.DataFrame:
    """Load dropdown data from a lookup table."""
    df = fetch_query(f"SELECT * FROM {table_name}")
    df.columns = [c.upper() for c in df.columns]
    return df

@st.cache_data
def load_books() -> pd.DataFrame:
    """Load book titles for selection."""
    books_df = fetch_query("SELECT ID, TITLE FROM BOOK")
    books_df.columns = [c.upper() for c in books_df.columns]
    return books_df

# --- HELPER FUNCTIONS ---
def get_author_id(full_name: str, authors_df: pd.DataFrame) -> int:
    """Get author ID from full name."""
    return int(authors_df[authors_df['FULL_NAME'] == full_name]['ID'].values[0])

def get_dropdown_id(name: str, df: pd.DataFrame) -> int:
    """Get ID from a lookup table by name."""
    return int(df[df['NAME'] == name]['ID'].values[0])

def find_selectbox_index(df: pd.DataFrame, id_col: str, current_val, list_to_search: List[str]) -> int:
    """Find the index of a value in a selectbox list."""
    try:
        name = df[df[id_col] == current_val].iloc[0].get('FULL_NAME', df[df[id_col] == current_val].iloc[0].get('NAME'))
        return list_to_search.index(name)
    except (IndexError, ValueError, KeyError):
        return 0

# --- PAGE CONFIGURATION (once at the top) ---
st.set_page_config(page_title="My Book Collection", layout="wide")

# --- APP LAYOUT ---
st.title("📚 Personal Library Manager")

tab1, tab2, tab3, tab4 = st.tabs(["📖 View Collection", "📝 Edit Books", "➕ Add Books", "➕ Add Author"])

# --- TAB 1: VIEWING ---
with tab1:
    st.header("📖 View Collection")
    
    # Load data
    df = load_books_collection()
    readings_df = load_readings()
    
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filters")
    search_term = st.sidebar.text_input("Search Title or Summary")
    
    # Build filter options, handling NaN values
    categories = [DEFAULT_FILTER_OPTION] + [cat for cat in df['CATEGORIES'].dropna().unique() if pd.notna(cat)]
    languages = [DEFAULT_FILTER_OPTION] + [lang for lang in df['LANGUAGE'].dropna().unique() if pd.notna(lang)]
    owners = [DEFAULT_FILTER_OPTION] + [owner for owner in df['OWNER'].dropna().unique() if pd.notna(owner)]
    statuses = [DEFAULT_FILTER_OPTION] + [status for status in df['STATUS'].dropna().unique() if pd.notna(status)]
    
    selected_category = st.sidebar.selectbox("Category", categories)
    selected_language = st.sidebar.selectbox("Language", languages)
    selected_owner = st.sidebar.selectbox("In Besitz?", owners)
    selected_status = st.sidebar.selectbox("Lesestatus", statuses)
    
    # --- FILTER LOGIC ---
    filtered_df = df.copy()
    
    if search_term:
        mask = (
            filtered_df['TITLE'].str.contains(search_term, case=False, na=False) | 
            filtered_df['SUMMARY'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[mask]
    
    if selected_category != DEFAULT_FILTER_OPTION:
        filtered_df = filtered_df[filtered_df['CATEGORIES'] == selected_category]
    
    if selected_language != DEFAULT_FILTER_OPTION:
        filtered_df = filtered_df[filtered_df['LANGUAGE'] == selected_language]
    
    if selected_owner != DEFAULT_FILTER_OPTION:
        filtered_df = filtered_df[filtered_df['OWNER'] == selected_owner]
    
    if selected_status != DEFAULT_FILTER_OPTION:
        filtered_df = filtered_df[filtered_df['STATUS'] == selected_status]
    
    # --- DISPLAY ---
    st.write(f"Zeigt {len(filtered_df)} Einträge")
    
    # Display books
    for _, row in filtered_df.iterrows():
        with st.container():
            st.subheader(row['TITLE'])
            st.write(f"**Author:** {row['AUTHOR_NAME']} | **Status:** {row['STATUS']}")
            
            # Filter readings for this specific book
            if pd.notna(row['ID']):
                book_readings = readings_df[readings_df['book_id'] == row['ID']]
                if not book_readings.empty:
                    dates_str = " | ".join([f"{r['start']} to {r['end']}" for _, r in book_readings.iterrows()])
                    st.caption(f"📖 **Read on:** {dates_str}")
        
        with st.expander("Zusammenfassung ausklappen"):
            st.write(row['SUMMARY'])
        st.divider()

# --- TAB 2: EDIT ENTRIES ---
with tab2:
    st.header("📝 Manage Entries")
    
    # 1. LOAD DATA (Missing in your previous snippet)
    authors_df_tab2 = load_authors()
    author_list = sorted(authors_df_tab2['FULL_NAME'].unique().tolist())
    
    # Load lookup tables for potential future use or other fields
    statuses = load_dropdown_data("STATUS")
    owners = load_dropdown_data("OWNER")
    languages = load_dropdown_data("LANGUAGES")
    
    # Load books for the selection dropdown
    books_df = load_books()
    book_titles = sorted(books_df['TITLE'].tolist())
    
    # 2. SELECTION UI
    st.subheader("📝 Edit Existing Book")
    selected_book_title = st.selectbox(
        "Select a book to edit", 
        [DEFAULT_BOOK_SELECT] + book_titles, 
        key="edit_book_select"
    )
    
    if selected_book_title != DEFAULT_BOOK_SELECT:
        # Get the ID of the selected book
        book_id = int(books_df[books_df['TITLE'] == selected_book_title]['ID'].values[0])
        
        # Load specific book data from DB
        current_book = fetch_query("SELECT * FROM BOOK WHERE ID = ?", params=(book_id,))
        
        if not current_book.empty:
            # Prepare data for form
            current_book = current_book.iloc[0]
            current_book.index = [c.upper() for c in current_book.index]
            
            # --- SECTION 1: EDIT BOOK DETAILS (The Metadata Form) ---
            # --- SECTION 1: EDIT BOOK DETAILS ---
            with st.form("edit_book_form"):
                st.subheader("📖 Edit Book Details")
                
                # 1. Basic Text Inputs
                edit_title = st.text_input("Title", value=current_book['TITLE'])
                edit_summary = st.text_area("Summary", value=current_book['SUMMARY'])
                
                # 2. Dropdown Data Preparation
                # Get lists of names for the selectboxes
                status_list = statuses['NAME'].tolist()
                owner_list = owners['NAME'].tolist()
                
                # 3. Selectboxes with pre-selected current values
                edit_author = st.selectbox(
                    "Author", 
                    author_list, 
                    index=find_selectbox_index(authors_df_tab2, 'ID', current_book['AUTHOR'], author_list)
                )
                
                edit_status = st.selectbox(
                    "Status", 
                    status_list, 
                    index=find_selectbox_index(statuses, 'ID', current_book['STATUS_ID'], status_list)
                )
                
                edit_owner = st.selectbox(
                    "Owner", 
                    owner_list, 
                    index=find_selectbox_index(owners, 'ID', current_book['OWNER_ID'], owner_list)
                )
                
                # 4. Save Logic
                if st.form_submit_button("Update Book Details"):
                    if not edit_title:
                        st.error("Title cannot be empty.")
                    else:
                        # Convert selected names back to IDs
                        new_a_id = get_author_id(edit_author, authors_df_tab2)
                        new_s_id = get_dropdown_id(edit_status, statuses)
                        new_o_id = get_dropdown_id(edit_owner, owners)
                        
                        update_query = """
                        UPDATE BOOK 
                        SET TITLE = ?, SUMMARY = ?, AUTHOR = ?, STATUS_ID = ?, OWNER_ID = ? 
                        WHERE ID = ?
                        """
                        run_query(update_query, (
                            edit_title, 
                            edit_summary, 
                            int(new_a_id), 
                            int(new_s_id), 
                            int(new_o_id), 
                            book_id
                        ))
                        
                        st.success("Updated successfully!")
                        st.cache_data.clear() 
                        st.rerun()
                

            st.markdown("---")

            # --- SECTION 2: READING HISTORY (Independent of the Metadata Form) ---
            st.subheader("📊 Reading History")
            # Fetch readings for this book - Force uppercase columns for consistency
            readings = fetch_query("SELECT * FROM READINGS WHERE BOOK_ID = ?", params=(book_id,))
            readings.columns = [c.upper() for c in readings.columns]
            
            if not readings.empty:
                for _, r in readings.iterrows():
                    col1, col2, col3 = st.columns([3, 3, 1])
                    col1.write(f"**Start:** {r['START']}")
                    col2.write(f"**End:** {r['END']}")
                    # This button is OUTSIDE the form, so it triggers immediately
                    if col3.button("🗑️", key=f"del_{r['ID']}"):
                        run_query("DELETE FROM READINGS WHERE ID = ?", (int(r['ID']),))
                        st.rerun()
            else:
                st.info("No reading sessions recorded.")

            # --- SECTION 3: ADD NEW SESSION (Separate mini-form) ---
            with st.expander("➕ Add New Reading Session"):
                with st.form("new_reading_form", clear_on_submit=True):
                    col_start, col_end = st.columns(2)
                    new_start = col_start.date_input("Start Date")
                    new_end = col_end.date_input("End Date")
                    
                    if st.form_submit_button("Add Session"):
                        run_query(
                            "INSERT INTO READINGS (book_id, start, end) VALUES (?, ?, ?)",
                            (book_id, str(new_start), str(new_end))
                        )
                        st.success("Reading session added!")
                        st.cache_data.clear() # Clear cache here too
                        st.rerun()

# --- TAB 3: ADD BOOKS ---
with tab3:
    st.header("➕ Add Books")
    
    # 1. Refresh data for dropdowns
    authors_df_tab3 = load_authors()
    author_options = sorted(authors_df_tab3['FULL_NAME'].unique().tolist())
    
    statuses_df = load_dropdown_data("STATUS")
    owners_df = load_dropdown_data("OWNER")
    languages_df = load_dropdown_data("LANGUAGES")
    
    # Create the form
    with st.form("add_book_form", clear_on_submit=True):
        st.subheader("Book Metadata")
        
        col1, col2 = st.columns(2)
        with col1:
            new_title = st.text_input("Title*")
            new_isbn = st.text_input("ISBN")
        with col2:
            author_choice = st.selectbox("Author", author_options)
            new_categories = st.text_input("Categories (e.g. Fantasy, History)")

        new_summary = st.text_area("Summary")

        st.divider()
        st.subheader("Classification")
        c1, c2, c3 = st.columns(3)
        with c1:
            status_choice = st.selectbox("Status", statuses_df['NAME'].tolist())
        with c2:
            owner_choice = st.selectbox("Owner", owners_df['NAME'].tolist())
        with c3:
            lang_choice = st.selectbox("Language", languages_df['NAME'].tolist())
        
        submitted = st.form_submit_button("💾 Save Book to Library")

        if submitted:
            # 2. Validation
            if not new_title:
                st.error("The book title is required.")
            elif not author_choice:
                st.error("Please select or add an author first.")
            else:
                try:
                    # 3. Map names back to IDs using your helper functions
                    a_id = get_author_id(author_choice, authors_df_tab3)
                    s_id = get_dropdown_id(status_choice, statuses_df)
                    o_id = get_dropdown_id(owner_choice, owners_df)
                    l_id = get_dropdown_id(lang_choice, languages_df)
                    
                    # 4. SQL Insert (Check that your column names match exactly)
                    insert_query = """
                    INSERT INTO BOOK (TITLE, SUMMARY, ISBN, CATEGORIES, AUTHOR, STATUS_ID, OWNER_ID, LANGUAGE_ID)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    run_query(
                        insert_query, 
                        (new_title, new_summary, new_isbn, new_categories, int(a_id), int(s_id), int(o_id), int(l_id))
                    )
                    
                    st.success(f"✅ '{new_title}' has been added!")
                    
                    # 5. CRITICAL: Clear cache so Tab 1 and Tab 2 see the new book
                    st.cache_data.clear()
                    
                    # Optional: Small delay or rerun to refresh the UI
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Database Error: {e}")

# --- TAB 4: ADD AUTHOR ---
with tab4:
    st.header("➕ Add Author")
    
    with st.form("add_author_form", clear_on_submit=True):
        st.subheader("Add New Author")
        new_first_name = st.text_input("First name").strip()
        new_last_name = st.text_input("Last name").strip()
        
        submitted = st.form_submit_button("Save Author")
        
        if submitted:
            # 1. Validation
            if not new_first_name or not new_last_name:
                st.error("Both First Name and Last Name are required.")
            else:
                try:
                    # 2. Check for duplicates (case-insensitive)
                    # We use fetch_query which is already defined
                    check_query = """
                    SELECT 1 FROM AUTHOR 
                    WHERE UPPER(FIRSTNAME) = UPPER(?) AND UPPER(LASTNAME) = UPPER(?)
                    LIMIT 1
                    """
                    existing_author = fetch_query(check_query, params=(new_first_name, new_last_name))
                    
                    if not existing_author.empty:
                        st.warning(f"The author '{new_first_name} {new_last_name}' already exists.")
                    else:
                        # 3. Insert the new author
                        insert_query = """
                        INSERT INTO AUTHOR (FIRSTNAME, LASTNAME)
                        VALUES (?, ?)
                        """
                        run_query(insert_query, (new_first_name, new_last_name))
                        
                        st.success(f"✅ Successfully added {new_first_name} {new_last_name}!")
                        
                        # 4. THE FIX: Clear the cache so the new author appears in dropdowns
                        st.cache_data.clear()
                        
                        # 5. Rerun to refresh the author lists in other tabs
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error adding author: {str(e)}")

    # Optional: Display a small list of recently added authors for confirmation
    st.divider()
    st.subheader("Existing Authors")
    all_authors = load_authors() # This will fetch fresh data if cache was cleared
    if not all_authors.empty:
        # Show last 5 added authors
        st.write(", ".join(all_authors['FULL_NAME'].tail(10).tolist()))
