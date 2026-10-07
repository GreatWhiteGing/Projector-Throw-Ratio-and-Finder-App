import streamlit as st
import pandas as pd
import math
import re
import io

def parse_ratio_range(text):
    """Extract min and max throw ratio from a text string like '0.95 - 1.22:1'"""
    if pd.isna(text):
        return None, None
    
    # skip cells that are clearly not ratios
    cleaned = str(text).strip()
    skip_words = ["n/a", "fixed", "optional", "dvled", "cart", "stand", "mount", "series", "wall"]
    if any(word in cleaned.lower() for word in skip_words):
        return None, None
    
    # remove ":1" or ":2" ratio notation (colon followed by a single digit)
    cleaned = re.sub(r"\s*:\s*\d\b", "", cleaned)
    
    # find all decimal numbers (e.g. 0.95, 1.22, 10.8)
    numbers = re.findall(r"\d+\.\d+", cleaned)
    
    # if no decimals found, try whole numbers but only if they look like ratios (1-20)
    if not numbers:
        numbers = re.findall(r"\b([1-9]\d?)\b", cleaned)
    
    if not numbers:
        return None, None
    
    floats = [float(n) for n in numbers]
    
    # sanity check - throw ratios should be between 0.1 and 20
    floats = [f for f in floats if 0.1 <= f <= 20]
    
    if not floats:
        return None, None
    
    return min(floats), max(floats)

# unit conversions
def to_inches(value, unit):
    """Convert a measurement to inches"""
    if value is None or value <=0:
        return None
    return value * 12 if unit == "Feet" else value

def diagonal_to_width(diagonal, aspect_w, aspect_h):
    """Convert diagonal measurement to screen width"""
    if aspect_h == 0:
        return diagonal
    ratio = aspect_w / aspect_h
    return diagonal * (ratio / math.sqrt(1 + ratio ** 2))

# page config
st.set_page_config(
    page_title="Throw Ratio Calculator and Projector Finder",
    page_icon="📽️",
    layout="wide"
)

# header
st.title("Projector Throw Calculator and Finder")
st.markdown("<p style='color: gray;'>Helper to find throw ratio and find a fit</p>", unsafe_allow_html=True)

# layout - 2 columns
left, right = st.columns(2)

# --- LEFT: measurements
with left:
    st.subheader("Throw Distance")
    col_tv, col_tu = st.columns([3, 1])
    with col_tv:
        throw_val = st.number_input("Distance", min_value=0.0, step=0.1, format="%.2f")
    with col_tu:
        throw_unit = st.selectbox("Unit", ["Feet", "Inches"], key="throw_unit")
    st.subheader("Screen Size")
    screen_type = st.radio("Measure by", ["Width", "Diagonal"], horizontal=True)
    col_sv, col_su = st.columns([3, 1])
    with col_sv:
        screen_val = st.number_input("Screen Size", min_value=0.0, step=0.1, format="%.2f")
    with col_su:
        screen_unit = st.selectbox("Unit", ["Feet", "Inches"], key="screen_unit")

throw_in = to_inches(throw_val, throw_unit)
screen_in = to_inches(screen_val, screen_unit)
    
if screen_type == "Diagonal" and screen_in:
    screen_in = diagonal_to_width(screen_in, 16, 9)
if throw_in and screen_in and screen_in > 0:
    ratio = throw_in / screen_in
else:
    ratio = None

# --- RIGHT: results
with right:
    st.subheader("Throw Ratio")
    if ratio:
        st.metric(label="Throw Ratio", value=f"{ratio:.2f}")
    else:
        st.info("Enter measurements on the left to calculate the throw ratio")

st.divider()

st.subheader("Optoma Inventory")

# file upload        
uploaded_file = st.file_uploader("Upload the daily report", type=["xlsx", "xls"])

if uploaded_file:
    if "uploaded_name" not in st.session_state or uploaded_file.name != st.session_state["uploaded_name"]:
        st.session_state["file_data"] = uploaded_file.read()
        st.session_state["uploaded_name"] = uploaded_file.name
    
if "file_data" in st.session_state:
    xl = pd.ExcelFile(io.BytesIO(st.session_state["file_data"]))
    sheet_names = xl.sheet_names
    selected_sheet = st.selectbox("Select a sheet", sheet_names, key="sheet_name")
    df = pd.read_excel(io.BytesIO(st.session_state["file_data"]), selected_sheet)
    st.success(f"Loaded {st.session_state['uploaded_name']} - {len(df)} rows found")
    
    #set the columns to search on
    throw_ratio_col = st.selectbox("Select the throw ratio column", df.columns.to_list(), key="throw_ratio_col")
    optional_cols = ["- none -"] + df.columns.tolist()
    model_col = st.selectbox("Select the model name column", optional_cols, key="model_col")
    lumens_col = st.selectbox("Select the lumens column", optional_cols, key="lumens_col")
    resolution_col = st.selectbox("Select the resoultion column", optional_cols, key="resolution_col")
    
    working = df.copy()
    working[["_ratio_min", "_ratio_max"]] = working[throw_ratio_col].apply(
        lambda x: pd.Series(parse_ratio_range(x))
    )
    working = working.dropna(subset=["_ratio_min", "_ratio_max"])
    
    if ratio:
        tolerance = 0.05
        matched = working[
            (working["_ratio_min"] <= ratio + tolerance) &
            (working["_ratio_max"] >= ratio - tolerance)
        ]
        
        if matched.empty:
            st.warning("No projectors found for this throw ratio. Try adjusting the measurements")
        else:
            display_cols = {}
        
            if model_col != "- none -":
                display_cols["Model"] = matched[model_col]
        
            if resolution_col != "- none -":
                display_cols["Resolution"] = matched[resolution_col]
        
            if lumens_col != "- none -":
                display_cols["Lumens"] = matched[lumens_col]
        
            display_cols["Throw Ratio"] = matched[throw_ratio_col]
        
            result_df = pd.DataFrame(display_cols).reset_index(drop=True)
            result_df.index += 1
        
            st.dataframe(result_df, use_container_width=True)

else:
    st.info("Upload an excel file to get started")