import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- PAGE SETUP ---
st.set_page_config(page_title="PIB Scraper", layout="wide")
st.title("📰 PIB Press Release by keyword(by Harsh Jain)")
st.markdown("Fetch and filter press releases from the Government of India.")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("📅 Select Date")
    day = st.number_input("Day", min_value=0, max_value=31, value=9)
    month = st.number_input("Month", min_value=0, max_value=12, value=12)
    year = st.number_input("Year", min_value=2000, max_value=2030, value=2024)

# --- MAIN INPUTS ---
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("Enter Keyword to Filter (Optional):", placeholder="e.g. Finance, Modi, RBI")
with col2:
    st.write("##") # Spacer
    run_button = st.button("🚀 Fetch Releases", use_container_width=True)

# --- LOGIC FUNCTION ---
def fetch_pib_data(d, m, y, kw):
    target_date_str = f"{d}-{m}-{y}"
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
            st.error(f"❌ Error: Server returned status code {response_post.status_code}")
            return []

        final_soup = BeautifulSoup(response_post.content, "html.parser")
        
        # 4. Check Count (Debugging info)
        count_div = final_soup.find("div", {"class": "search_box_result"})
        if count_div:
            st.caption(f"Server Message: {count_div.text.strip()}")

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
        st.error(f"An error occurred: {e}")
        return []

# --- EXECUTION ---
if run_button:
    with st.spinner(f"Fetching data for {day}-{month}-{year}..."):
        data = fetch_pib_data(day, month, year, keyword)
        
        if data:
            st.success(f"✅ Found {len(data)} releases matching '{keyword}'")
            
            # Display as a dataframe (table)
            df = pd.DataFrame(data)
            
            # --- MODIFIED SECTION: Configuring the URL column ---
            st.dataframe(
                df,
                column_config={
                    "URL": st.column_config.LinkColumn(
                        "Article Link",     # The header name to display
                        display_text="Open" # Changes the long URL text to just "Open" (Cleaner UI)
                    )
                },
                use_container_width=True,
                hide_index=True  # Hides the 0,1,2 index numbers
            )
            # ----------------------------------------------------
            
            # CSV Download Button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"pib_data_{day}_{month}_{year}.csv",
                mime="text/csv",
            )
        else:
            st.warning("No releases found. Try a different date or remove the keyword.")