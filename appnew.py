import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
import concurrent.futures

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- PAGE SETUP ---
st.set_page_config(page_title="PIB Scraper", layout="wide")
st.title("📰 PIB Press Release Scraper")
st.markdown("Fetch and filter press releases from the Government of India.")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("⚙️ Search Configuration")
    
    # 1. Select Search Mode
    search_mode = st.radio(
        "Select Search Mode:",
        ("Specific Date", "Search by Months")
    )
    
    st.divider()

    # Variables to store user choices
    selected_day = 0
    selected_months = []
    selected_year = 2024

    # MODE A: Specific Date (Original Functionality)
    if search_mode == "Specific Date":
        st.subheader("📅 Select Date")
        selected_day = st.number_input("Day", min_value=1, max_value=31, value=9)
        # Single month selection for date mode
        m_input = st.number_input("Month", min_value=1, max_value=12, value=12)
        selected_months = [m_input] # Store as list for consistent processing later
        selected_year = st.number_input("Year", min_value=2000, max_value=2030, value=2024)

    # MODE B: Multiple Months (New Functionality)
    else:
        st.subheader("🗓️ Select Months")
        selected_year = st.number_input("Year", min_value=2000, max_value=2030, value=2024)
        
        # Month Name to Number Mapping
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4, 
            "May": 5, "June": 6, "July": 7, "August": 8, 
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        
        month_names = st.multiselect(
            "Select Months (Select any number of months):",
            list(month_map.keys()),
            default=["January"]
        )
        
        # Convert names to numbers (e.g., ['January', 'March'] -> [1, 3])
        selected_months = [month_map[m] for m in month_names]
        
        # In this mode, Day is always 0
        selected_day = 0

# --- MAIN INPUTS ---
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("Enter Keyword to Filter (Optional):", placeholder="e.g. Finance, Modi, RBI")
with col2:
    st.write("##") # Spacer
    run_button = st.button("🚀 Fetch Releases", use_container_width=True)

# --- LOGIC FUNCTION ---
def fetch_pib_data(d, m, y, kw):
    # If d is 0, we format the date string differently for display, or just keep it simple
    target_date_str = f"{d}-{m}-{y}" if d != 0 else f"Month-{m}-{y}"
    
    base_url = "https://www.pib.gov.in/allRel.aspx?reg=3&lang=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.pib.gov.in",
        "Referer": base_url
    }

    session = requests.Session()

    try:
        # 1. Get Session Tokens
        response_get = session.get(base_url, headers=headers, verify=False)
        soup_get = BeautifulSoup(response_get.content, "html.parser")

        viewstate = soup_get.find("input", {"id": "__VIEWSTATE"})["value"]
        eventvalidation = soup_get.find("input", {"id": "__EVENTVALIDATION"})["value"]
        viewstategen = soup_get.find("input", {"id": "__VIEWSTATEGENERATOR"})["value"]

        # 2. Prepare Payload
        payload = {
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlday", 
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategen,
            "__VIEWSTATEENCRYPTED": "",
            "__EVENTVALIDATION": eventvalidation,
            "ctl00$Bar1$ddlregion": "3",
            "ctl00$Bar1$ddlLang": "1",
            "ctl00$ContentPlaceHolder1$hydregionid": "3",
            "ctl00$ContentPlaceHolder1$hydLangid": "1",
            "ctl00$ContentPlaceHolder1$ddlMinistry": "0",
            "ctl00$ContentPlaceHolder1$ddlday": str(d),       
            "ctl00$ContentPlaceHolder1$ddlMonth": str(m),    
            "ctl00$ContentPlaceHolder1$ddlYear": str(y)      
        }

        # 3. Post Request
        response_post = session.post(base_url, headers=headers, data=payload, verify=False)
        
        if response_post.status_code != 200:
            return []

        final_soup = BeautifulSoup(response_post.content, "html.parser")
        
        # 5. Parse Links
        results = []
        content_area = final_soup.find("div", {"class": "content-area"})
        
        if content_area:
            all_links = content_area.find_all("a", href=True)

            for link in all_links:
                href = link['href']
                if "PressReleasePage.aspx" in href or "relid=" in href.lower():
                    title = link.get('title', '').strip()
                    if not title: 
                        title = link.text.strip()
                    
                    if title:
                        full_url = "https://www.pib.gov.in" + href if not href.startswith("http") else href
                        
                        # Filter Logic
                        if not kw or kw.lower() in title.lower():
                            results.append({"Title": title, "URL": full_url, "Date": target_date_str})
        
        return results

    except Exception as e:
        return []

# --- EXECUTION ---
if run_button:
    all_data = []
    
    # Check if user actually selected months in Month mode
    if search_mode == "Search by Months" and not selected_months:
        st.error("⚠️ Please select at least one month.")
    else:
        info_text = f"Fetching data for {selected_day}-{selected_months[0]}-{selected_year}" if search_mode == "Specific Date" else f"Fetching data for selected months in {selected_year}..."
        
        with st.spinner(info_text):
            
            # PARALLEL PROCESSING FOR MONTHS
            # We use ThreadPoolExecutor to hit the website for all selected months at the same time
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Create a list of tasks to run
                futures = []
                for m in selected_months:
                    # fetch_pib_data(day, month, year, keyword)
                    # Note: selected_day is 0 for Month mode, and specific day for Date mode
                    futures.append(executor.submit(fetch_pib_data, selected_day, m, selected_year, keyword))
                
                # Gather results as they finish
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    all_data.extend(result)
        
        # --- DISPLAY RESULTS ---
        if all_data:
            st.success(f"✅ Found {len(all_data)} releases matching '{keyword}'")
            
            # Display as a dataframe (table)
            df = pd.DataFrame(all_data)
            
            st.dataframe(
                df,
                column_config={
                    "URL": st.column_config.LinkColumn(
                        "Article Link",     
                        display_text="Open" 
                    )
                },
                use_container_width=True,
                hide_index=True 
            )
            
            # CSV Download Button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"pib_data_results.csv",
                mime="text/csv",
            )
        else:
            st.warning("No releases found. Try a different date")
