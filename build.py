import requests
from bs4 import BeautifulSoup
import os
import sys
import traceback
import base64
from datetime import datetime

def build_mountain_dashboard():
    # 1. Configuration
    mwis_text_url = 'https://www.mwis.org.uk/forecasts/scottish/southeastern-highlands/text'
    synoptic_url = 'https://www.mwis.org.uk/forecasts/synoptic-charts'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # 2. Fetch Synoptic Chart (And Base64 Encode it for TRMNL)
    chart_base64 = None
    try:
        res = requests.get(synoptic_url, headers=headers, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if ('chart' in src.lower() or 'synoptic' in src.lower()) and 'logo' not in src.lower():
                chart_src = "https://www.mwis.org.uk" + src if src.startswith('/') else src
                
                # The NAS downloads the actual image file
                img_res = requests.get(chart_src, headers=headers, timeout=30)
                img_res.raise_for_status()
                
                # Convert the raw image bytes into a Base64 text string
                b64_data = base64.b64encode(img_res.content).decode('utf-8')
                img_type = "png" if ".png" in chart_src.lower() else "jpeg"
                
                # Format it for HTML embedding
                chart_base64 = f"data:image/{img_type};base64,{b64_data}"
                break
    except Exception as e:
        # Isolated Soft-Fail: If the image breaks, we still want the text forecast to update.
        print(f"Warning: Could not fetch or encode synoptic chart. {e}")

    # 3. Fetch and Parse Text Data
    area_summary = "Summary unavailable."
    planning_outlook = "Outlook unavailable."
    trmnl_se_date = "Today"

    res = requests.get(mwis_text_url, headers=headers, timeout=30)
    res.raise_for_status()
    raw_text = BeautifulSoup(res.text, 'html.parser').get_text(separator='\n')
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

    # Extract Summary
    for i, line in enumerate(lines):
        if "summary" in line.lower() and i + 1 < len(lines):
            area_summary = lines[i+1]
            break

    # Extract Outlook
    for i, line in enumerate(lines):
        if ("planning outlook" in line.lower() or "looking ahead" in line.lower()) and i + 1 < len(lines):
            planning_outlook = lines[i+1]
            break

    # Extract Date
    found_viewing_marker = False
    for line in lines:
        if "viewing forecast for" in line.lower():
            found_viewing_marker = True
            
        if found_viewing_marker and any(day in line for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
            trmnl_se_date = line.strip()
            break
            
    # Fallback Date
    if trmnl_se_date == "Today":
        for line in lines:
             if any(day in line for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
                 if len(line) < 40 and not any(word in line.lower() for word in ["summary", "outlook", "wind", "cloud"]):
                     trmnl_se_date = line.strip()
                     break

    # 4. Generate Layout
    trmnl_img = f'<img src="{chart_base64}" />' if chart_base64 else "<p>No synoptic chart available.</p>"

    total_chars = len(area_summary) + len(planning_outlook)

    t_body_size = "12pt"
    t_header_size = "17pt"

    # Dynamic scaling to prevent text clipping on TRMNL
    if total_chars > 1150:
        t_body_size = "9pt"
        t_header_size = "15pt"
    elif total_chars > 830:
        t_body_size = "10pt"
        t_header_size = "16pt"
    elif total_chars > 680:
        t_body_size = "11pt"
        t_header_size = "16pt"

    trmnl_tmpl = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,300;0,400;0,700;1,300&display=swap" rel="stylesheet" />
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{{box-sizing:border-box;}}

/* TRMNL STRICT DEFAULTS */
body{{
    margin:0; padding:0;
    width:800px; height:480px; 
    background:#fff; color:#000; 
    font-family:Georgia,serif;
    overflow:hidden; 
    display:flex; flex-direction:column;
}}
.main-content{{display:flex;width:100%;flex-grow:1;flex-direction:row;}}
.left-pane{{width:50%;height:100%;padding:25px 12px 25px 25px;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;}}
.left-pane img{{max-width:100%;max-height:100%;object-fit:contain;}}
.right-pane{{width:50%;height:100%;padding:25px 25px 25px 13px;display:flex;flex-direction:column;}}
.date-header{{font-size:{t_header_size};font-weight:bold;margin-top:-5px;margin-bottom:5px;display:block;}}
.body-text{{font-size:{t_body_size};line-height:1.2;margin:0 0 15px 0;}}
.outlook-section{{flex-grow:1;overflow:hidden;}}

.mobile-links {{ display: none; }}

/* MOBILE & KINDLE ESCAPE HATCH */
@media screen and (max-width: 799px), screen and (orientation: portrait) {{
    body {{ 
        width: auto; height: auto; min-height: 100vh;
        overflow: auto; 
        font-family: "Merriweather", serif;
        line-height: 1.5;
    }}
    .main-content {{ flex-direction: column; width: 95%; margin: 0 auto; }}
    .left-pane {{ width: 100%; height: auto; padding: 15px 20px 5px 20px; }}
    .right-pane {{ width: 100%; height: auto; padding: 5px 20px 15px 20px; }}
    .outlook-section {{ overflow: visible; }}
    
    .date-header {{ font-size: 28px; margin-top: 0; line-height: 1.4; }}
    .body-text {{ font-size: 16px; line-height: 1.5; margin-bottom: 15px; }}
    
    .mobile-links {{ display: block; margin-top: 16px; font-size: 20px; }}
    .mobile-links a {{ color: #000; text-decoration: none; }}
    
    .mobile-links summary {{ 
        cursor: pointer; 
        font-weight: normal; 
        margin-bottom: 8px; 
        list-style: none; 
    }}
    .mobile-links summary::-webkit-details-marker {{ display: none; }}
    
    .mobile-links ul {{ margin: 0; padding-left: 30px; list-style-type: none; }}
    .mobile-links li {{ margin-bottom: 8px; }}
    .mobile-links details {{ margin-bottom: 12px; }}
}}
</style></head><body><div class="main-content">
<div class="left-pane">{trmnl_img}</div>
<div class="right-pane">
    <div class="summary-section">
        <span class="date-header">{trmnl_se_date}</span>
        <p class="body-text">{area_summary}</p>
    </div>
    <div class="outlook-section">
        <p class="body-text">{planning_outlook}</p>
        
        <div class="mobile-links">
            <details open>
                <summary>MWIS forecasts</summary>
                <ul>
                    <li><a href="https://www.mwis.org.uk/forecasts/scottish/southeastern-highlands/text">SE Highlands</a></li>
                    <li><a href="https://www.mwis.org.uk/forecasts/scottish/cairngorms-np-and-monadhliath/text">Cairngorms</a></li>
                    <li><a href="https://www.mwis.org.uk/forecasts/scottish/west-highlands/text">West Highlands</a></li>
                    <li><a href="https://www.mwis.org.uk/forecasts/scottish/the-northwest-highlands/text">NW Highlands</a></li>
                    <li><a href="https://www.mwis.org.uk/">MWIS home</a></li>
                </ul>
            </details>
            <details>
                <summary>SAIS forecasts</summary>
                <ul>
                    <li><a href="https://www.sais.gov.uk/southern-cairngorms/">S Cairngorms</a></li>
                    <li><a href="https://www.sais.gov.uk/northern-cairngorms/">N Cairngorms</a></li>
                    <li><a href="https://www.sais.gov.uk/glencoe/">Glen Coe</a></li>
                    <li><a href="https://www.sais.gov.uk/lochaber/">Lochaber</a></li>
                    <li><a href="https://www.sais.gov.uk/creag-meagaidh/">Creag Meagaidh</a></li>
                    <li><a href="https://www.sais.gov.uk/torridon/">Torridon</a></li>
                    <li><a href="https://www.sais.gov.uk/">SAIS home</a></li>
                </ul>
            </details>
        </div>
    </div>
</div>
</div></body></html>"""

    # 5. Save HTML output (Absolute Path for Synology Cron Job)
    output_path = "/var/services/homes/alex/scripts/mountainweather/trmnl.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(trmnl_tmpl)

if __name__ == "__main__":
    try:
        build_mountain_dashboard()
    except Exception as e:
        base_path = "/var/services/homes/alex/scripts/mountainweather"
        log_dir = os.path.join(base_path, "logs")

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        log_filename = f"error_{timestamp}.txt"
        
        error_msg = f"Crash at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        error_msg += traceback.format_exc()

        # Write to persistent log directory
        with open(os.path.join(log_dir, log_filename), "w") as f:
            f.write(error_msg)
            
        # Write to temporary file for the shell script to catch and email
        with open(os.path.join(base_path, "python_error.txt"), "w") as f:
            f.write(error_msg)
            
        print("Python execution failed. Logs written.")
        sys.exit(1)