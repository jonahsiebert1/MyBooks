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

tab1, tab2, tab3 = st.tabs(["📖 View Collection", "📝 Edit Books", "➕ Add Books"])

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
    
    # 1. Fetch and clean Author data
    authors = pd.read_sql_query("SELECT ID, FIRSTNAME, LASTNAME FROM AUTHOR", conn)
    authors.columns = [c.upper() for c in authors.columns]
    
    # Replace NaN/None with empty strings so the addition (+) doesn't fail
    authors['FIRSTNAME'] = authors['FIRSTNAME'].fillna('')
    authors['LASTNAME'] = authors['LASTNAME'].fillna('')
    
    # Create the display name
    authors['FULL_NAME'] = authors['LASTNAME'] + ", " + authors['FIRSTNAME']
    
    # Clean up any trailing commas if one name was missing
    authors['FULL_NAME'] = authors['FULL_NAME'].str.strip(", ")
    
    # Get a clean, sorted list
    author_list = sorted(authors['FULL_NAME'].unique().tolist())

    # 2. Fetch other dropdown data (with uppercase fix)
    def get_dropdown_data(table_name, conn):
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        df.columns = [c.upper() for c in df.columns]
        return df

    statuses = get_dropdown_data("STATUS", conn)
    owners = get_dropdown_data("OWNER", conn)
    languages = get_dropdown_data("LANGUAGES", conn)
    
    # 3. Fetch Books for editing
    books_df = pd.read_sql_query("SELECT ID, TITLE FROM BOOK", conn)
    books_df.columns = [c.upper() for c in books_df.columns]
    book_titles = sorted(books_df['TITLE'].tolist())
    
    conn.close()

    # --- UI SECTION ---
    st.subheader("📝 Edit Existing Book")
    selected_book_title = st.selectbox("Select a book to edit", ["-- Choose a Book --"] + book_titles)

    if selected_book_title != "-- Choose a Book --":
        book_id = books_df[books_df['TITLE'] == selected_book_title]['ID'].values[0]
        
        with get_db_connection() as conn:
            # Using query parameters (?) to prevent SQL injection and handle titles with quotes
            current_book = pd.read_sql_query("SELECT * FROM BOOK WHERE ID = ?", conn, params=(int(book_id),)).iloc[0]
            current_book.index = [c.upper() for c in current_book.index]

        with st.form("edit_book_form"):
            edit_title = st.text_input("Title", value=current_book['TITLE'])
            edit_summary = st.text_area("Summary", value=current_book['SUMMARY'])
            
            # Helper to find current index for the selectbox default
            def find_idx(df, id_col, current_val, list_to_search):
                try:
                    # Get the name associated with the ID in the record
                    name = df[df[id_col] == current_val].iloc[0].get('FULL_NAME', df[df[id_col] == current_val].iloc[0].get('NAME'))
                    return list_to_search.index(name)
                except:
                    return 0

            edit_author = st.selectbox("Author", author_list, 
                                      index=find_idx(authors, 'ID', current_book['AUTHOR'], author_list))
            
            save_changes = st.form_submit_button("Update Book")

            if save_changes:
                new_a_id = authors[authors['FULL_NAME'] == edit_author]['ID'].values[0]
                
                update_query = """
                UPDATE BOOK 
                SET TITLE = ?, SUMMARY = ?, AUTHOR = ?
                WHERE ID = ?
                """
                run_query(update_query, (edit_title, edit_summary, int(new_a_id), int(book_id)))
                st.success(f"Updated '{edit_title}' successfully!")
                st.rerun()

    with tab3:
        st.header("Add Entries")
        
        conn = get_db_connection()
        
        # Load and force all column names to UPPERCASE to avoid KeyErrors
        authors = pd.read_sql_query("SELECT * FROM AUTHOR", conn)
        authors.columns = [c.upper() for c in authors.columns]

        # Handle empty values (NaN) so the code doesn't crash
        authors['FIRSTNAME'] = authors['FIRSTNAME'].fillna('')
        authors['LASTNAME'] = authors['LASTNAME'].fillna('')
        
        # 2. Create the combined name column
        # This creates a "Lastname, Firstname" format
        authors['FULL_NAME'] = authors['LASTNAME'] + ", " + authors['FIRSTNAME']
        
        # Optional: Clean up trailing commas if Firstname was empty
        authors['FULL_NAME'] = authors['FULL_NAME'].str.strip(", ")
        
        # 3. Create the sorted list for the dropdown
        author_options = sorted(authors['FULL_NAME'].unique().tolist())
        
        statuses = pd.read_sql_query("SELECT * FROM STATUS", conn)
        statuses.columns = [c.upper() for c in statuses.columns]
        
        owners = pd.read_sql_query("SELECT * FROM OWNER", conn)
        owners.columns = [c.upper() for c in owners.columns]
        
        languages = pd.read_sql_query("SELECT * FROM LANGUAGES", conn)
        languages.columns = [c.upper() for c in languages.columns]
        
        conn.close()
    
        # Create the form
        with st.form("add_book_form", clear_on_submit=True):
            st.subheader("Add New Book")
            new_title = st.text_input("Title")
            new_summary = st.text_area("Summary")
            new_isbn = st.text_input("ISBN")
            
            # Use UPPERCASE keys here to match the transformation above
            # author_choice = st.selectbox("Author", authors['LASTNAME'].tolist())
            # 4. Update the Selectbox
            author_choice = st.selectbox("Author", author_options)
            
            status_choice = st.selectbox("Status", statuses['NAME'].tolist())
            owner_choice = st.selectbox("Owner", owners['NAME'].tolist())
            lang_choice = st.selectbox("Language", languages['NAME'].tolist())
            
            # This button MUST be inside the 'with st.form' block
            submitted = st.form_submit_button("Save Book")
    
            if submitted:
                if not new_title:
                    st.warning("Please provide a title.")
                else:
                    # Map names back to IDs using UPPERCASE keys
                    # 5. Get the ID back for the database (when saving)
                    a_id = authors[authors['FULL_NAME'] == author_choice]['ID'].values[0]
                    # a_id = authors[authors['LASTNAME'] == author_choice]['ID'].values[0]
                    s_id = statuses[statuses['NAME'] == status_choice]['ID'].values[0]
                    o_id = owners[owners['NAME'] == owner_choice]['ID'].values[0]
                    l_id = languages[languages['NAME'] == lang_choice]['ID'].values[0]
    
                    insert_query = """
                    INSERT INTO BOOK (TITLE, SUMMARY, ISBN, AUTHOR, STATUS_ID, OWNER_ID, LANGUAGE_ID)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                    run_query(insert_query, (new_title, new_summary, new_isbn, int(a_id), int(s_id), int(o_id), int(l_id)))
                    st.success(f"Successfully added {new_title}!")
                    st.rerun()
