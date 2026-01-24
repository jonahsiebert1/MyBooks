import streamlit as st
import sqlite3
import pandas as pd

# Page configuration
st.set_page_config(page_title="My Book Collection", layout="wide")

import os

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
