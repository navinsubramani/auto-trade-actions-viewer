import os
import streamlit as st
import pandas as pd
from streamlit_shortcuts import add_shortcuts
from streamlit_calendar import calendar

from stocklogdata import StockLogData

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set the page configuration
st.set_page_config(
    page_title="AI Stock Options",
    page_icon=":guardsman:",
    layout="wide",
)
# Add Note to the top of the page
st.info("Note: This page is for viewing the GenAI algo training data and results. This is a experiemental and research page and the data is not used for trading or any finicial advice.")

# Read the content from the .data folder
DATA_FOLDER = os.getenv("DATA_FOLDER", "")
stockdata = StockLogData(folder_path=DATA_FOLDER)
daystats, tradestats = stockdata.find_day_stats()
#st.write(daystats)
#st.write(tradestats)

last_date = daystats["Date"].max()

# Define State Variables
if "selected_date" not in st.session_state:
    st.session_state.selected_date = str(last_date)
if "selected_index" not in st.session_state:
    st.session_state.selected_index = -1

sel1, sel2, sel3 = st.columns([1.3, 0.5, 1.5])


with sel1:

    mode = sel1.selectbox(
        "Calendar Mode:",
        (
            "daygrid",
            "timegrid",
            "timeline",
            "list",
            "multimonth",
        ),
    )

    # Create a Calendar widget
    # Increase the height of the calendar
    calendar_options = {
        "editable": True,
        "selectable": True,
        "slotMinTime": "08:00:00",
        "slotMaxTime": "18:00:00",
        "resourceGroupField": "Stock Name",
        "resources": [
            {"id": "nvda", "stock_name": "NVIDIA"},
        ],
    }

    # Create calendar events using the tradestats data
    calendar_events = []
    for index, row in tradestats.iterrows():
        # tradestats has columns: Date, entry_time, exit_time, trade_type, entry_price, exit_price, profit_loss, max_drawdown, max_drawup
        # event should have start and start in format "2023-07-31T08:30:00"
        # Dark red for loss, dark green for profit
        event = {
            "title": f"{row['trade_type']} ${row['profit_loss']:.2f}",
            "start": f"{row['Date']}T{row['entry_time']}",
            "end": f"{row['Date']}T{row['exit_time']}",
            "resourceId": "nvda",
            "backgroundColor": "red" if row['profit_loss'] < 0 else "green",
        }
        calendar_events.append(event)

    for index, row in daystats.iterrows():
        # daystats has columns: Date, open, high, low, close, volume
        # event should have start and end in format "2023-07-31T08:30:00"
        event = {
            "title": f"#{row['trade_count']} for ${row['day_profit_loss']:.2f}",
            "start": f"{row['Date']}",
            "backgroundColor": "red" if row['day_profit_loss'] < 0 else "green",
            "allDay": True,
        }
        calendar_events.append(event)

    # Custom CSS for the calendar
    custom_css="""
        .fc-event-past {
            opacity: 0.8;
        }
        .fc-event-time {
            font-style: italic;
        }
        .fc-event-title {
            font-weight: 700;
        }
        .fc-toolbar-title {
            font-size: 2rem;
        }
    """

    if mode == "daygrid":
        calendar_options = {
            **calendar_options,
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "dayGridDay,dayGridWeek,dayGridMonth",
            },
            "initialDate": f"{last_date}",
            "initialView": "dayGridMonth",
        }
    elif mode == "timegrid":
        calendar_options = {
            **calendar_options,
            "initialView": "timeGridWeek",
        }
    elif mode == "timeline":
        calendar_options = {
            **calendar_options,
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "timelineDay,timelineWeek,timelineMonth",
            },
            "initialDate": f"{last_date}",
            "initialView": "timelineMonth",
        }
    elif mode == "list":
        calendar_options = {
            **calendar_options,
            "initialDate": f"{last_date}",
            "initialView": "listMonth",
        }
    elif mode == "multimonth":
        calendar_options = {
            **calendar_options,
            "initialView": "multiMonthYear",
        }

    calendar_result = calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css=custom_css,
        key='calendar', # Assign a widget key to prevent state loss
    )
    #sel1.write(calendar_result)

    selected_date = calendar_result['eventClick']['event']['start'] if calendar_result and 'eventClick' in calendar_result else ""

    # Convert selected_date to a "YYYY-MM-DD" format from "2025-06-30T11:42:00-04:00"
    if selected_date:
        selected_date = selected_date.split("T")[0]
        st.session_state.selected_date = selected_date
        st.session_state.selected_index = -1  # Reset selected index when date changes
    else:
        pass


# Display the first column with a dataframe but only specific columns
with sel2:
    daydata, images_folder_path = stockdata.get_day_data(st.session_state.selected_date)
    if daydata is not None and not daydata.empty:
        st.markdown(f"##### Data for {st.session_state.selected_date}")
        selection = st.dataframe(
            daydata[["Time", "Stock Price", "AI Recommendation"]],
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            height=780,
            key="daydata_table",
        )
        selected_index = selection["selection"]["rows"] if selection is not None else []
        default_index = -1 if daydata.empty else 0
        st.session_state.selected_index = selected_index[0] if isinstance(selected_index, list) and selected_index else default_index
    
    else:
        st.warning(f"No data available for the date - {st.session_state.selected_date}. Select a date in the calendar to view data.")

# If I move mouse arrow up and down over a row, display the data in the next rows up and down


with sel3:
    selected_index = st.session_state.selected_index
    if selected_index != -1:
        try:
            # Get the Screenshot Path from daydata for the selected_index and display the image

            try:
                image_path = daydata.iloc[selected_index]["Screenshot Path"]
                image_name = os.path.basename(image_path)
                image_files = []
                if images_folder_path:
                    # List all image files in the folder
                    for root, dirs, files in os.walk(images_folder_path):
                        for file in files:
                            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                image_files.append(os.path.join(root, file))

                for image_file in image_files:
                    if os.path.basename(image_file) == image_name:
                        st.image(image_file, caption=image_name)
                        break
            except Exception as e:
                st.warning("Image not found for the selected trade entry. Please check the data or the image path.")

            st.markdown("**Reason:**")
            st.write(str(daydata.iloc[selected_index]["Reason"]))
            st.markdown("**Note:**")
            st.write(str(daydata.iloc[selected_index]["Note"]))
            st.write(f"AI Recommendation: {str(daydata.iloc[selected_index]["AI Recommendation"])}, Confidence: {str(daydata.iloc[selected_index]["Confidence"])}")

        except Exception as e:
            st.error(f"Error displaying data: {e}")