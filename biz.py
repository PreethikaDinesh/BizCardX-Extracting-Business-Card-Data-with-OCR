import streamlit as st
import mysql.connector
import easyocr
import re
import pandas as pd

# Initialize EasyOCR
reader = easyocr.Reader(['en'])

# Connect to MySQL database
mysql_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="bizcard"
)
cursor = mysql_conn.cursor()

# Function to create MySQL table
def create_table():
    create_query = '''CREATE TABLE IF NOT EXISTS card_data(
                    Company_name VARCHAR(255),
                    Card_holder VARCHAR(255),
                    Designation VARCHAR(255),
                    Mobile_number VARCHAR(255),
                    Email VARCHAR(255),
                    Website VARCHAR(255),
                    Area VARCHAR(255),
                    City VARCHAR(255),
                    State VARCHAR(255),
                    Pin_code VARCHAR(255)
                     )'''
    cursor.execute(create_query)
    mysql_conn.commit()

# Function to extract data from OCR result
def get_data(res):
    data = {
        "company_name": "",
        "card_holder": "",
        "designation": "",
        "mobile_number": "",
        "email": "",
        "website": "",
        "area": "",
        "city": "",
        "state": "",
        "pin_code": ""
    }
    mobile_numbers=[]
    for ind, i in enumerate(res):
        # To get WEBSITE_URL
        if any(sub in i.lower() for sub in ["www", "http", "https"]):
            data["website"] = i
         # To get COMPANY NAME
        elif ind == len(res) - 1:
            data["company_name"] = i
        # To get EMAIL ID
        elif "@" in i:
            data["email"] = i
        # To get MOBILE NUMBER
        if "-" in i:
              mobile_numbers.append(i)   # Append mobile number to the list
    # Join the mobile numbers if there are two
        if len(mobile_numbers) == 2:
            data["mobile_number"] = " & ".join(mobile_numbers)
        elif len(mobile_numbers) == 1:
            data["mobile_number"] = mobile_numbers[0]
        # To get CARD HOLDER NAME
        elif ind == 0:
            data["card_holder"]=i
        # To get DESIGNATION
        elif ind == 1:
            data["designation"] = i
        # To get AREA
        if re.findall('^[0-9].+, [a-zA-Z]+', i):
            data["area"] = i.split(',')[0]
        elif re.findall('[0-9] [a-zA-Z]+', i):
            data["area"] = i
        # To get CITY NAME
        match1 = re.match(r'.+St , ([a-zA-Z]+).+', i)
        match2 = re.match(r'.+St,, ([a-zA-Z]+).+', i)
        match3 = re.match(r'^[E].*', i)
        if match1:
            data["city"] = match1.group(1)
        elif match2:
            data["city"] = match2.group(1)
        elif match3:
            data["city"] = match3.group()
        # To get STATE
        state_match = re.match(r'([a-zA-Z]{9}) +([0-9])', i)
        if state_match:
            data["state"] = state_match.group(1)
        elif re.match(r'^[0-9].+, ([a-zA-Z]+);', i):
            data["state"] = i.split()[-1]
        # To get PINCODE
        if len(i) >= 6 and i.isdigit():
            data["pin_code"] = i
        elif re.match(r'[a-zA-Z]{9} +([0-9])', i):
            data["pin_code"] = i[10:]
    return data

# Function to insert data into MySQL table

def insert_data():
    try:
        uploaded_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            # Read text from the uploaded image
            image_bytes = uploaded_file.read()
            ocr_result = reader.readtext(image_bytes, detail=0)

            # Extract data from OCR result
            data = get_data(ocr_result)
             # Display the uploaded image
            st.image(image_bytes, caption='Uploaded Image', use_column_width=True)
             # Display the extracted data in a table
            st.write("Extracted Data:")
            df = pd.DataFrame([data])  # Convert data dictionary to DataFrame
            column_names = ["Company Name", "Card Holder", "Designation", "Mobile Number", 
                "Email", "Website", "Area", "City", "State", "Pin Code"]
            df.columns = column_names  # Set column names
            st.table(df)

            # Create MySQL table
            create_table()

            # Insert data into MySQL table
            insert_query = """INSERT INTO card_data
                              (Company_name, Card_holder, Designation, Mobile_number, Email, Website, Area, City, State, Pin_code)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            # Execute the insert query for each row of data
            cursor.execute(insert_query, (data["company_name"], data["card_holder"], data["designation"],
                                           data["mobile_number"], data["email"], data["website"],
                                           data["area"], data["city"], data["state"], data["pin_code"]))
            mysql_conn.commit()
            st.success("Data inserted successfully!")
            return data
    except mysql.connector.Error as err:
        st.error(f"Error inserting data: {err}")
       

# Function to update data in the database
def update_data(company_name, field, new_value):
    try:
        query = f"UPDATE card_data SET {field} = %s WHERE Company_name = %s"
        cursor.execute(query, (new_value, company_name))
        mysql_conn.commit()
        st.success("Data updated successfully.")
    except mysql.connector.Error as err:
        st.error(f"Error updating data: {err}")

# Function to fetch updated data from the database
def fetch_updated_data(company_name):
    try:
        query = "SELECT * FROM card_data WHERE Company_name = %s"
        cursor.execute(query, (company_name,))
        updated_data = cursor.fetchone()
        return updated_data
    except mysql.connector.Error as err:
        st.error(f"Error fetching updated data: {err}")

# Function to delete data from the database by company name
def delete_data(company_name):
    try:
        # Consume any unread results
        while cursor.nextset():
            pass
        
        query = "DELETE FROM card_data WHERE Company_name = %s"
        cursor.execute(query, (company_name,))
        mysql_conn.commit()
        st.success("Data deleted successfully.")
    except mysql.connector.Error as err:
        st.error(f"Error deleting data: {err}")

# Streamlit UI
st.title("Business Card OCR")

# Radio button to select option
select_option = st.radio("Select Option", [" ","Insert Data", "Update Data", "Fetch Updated Data", "Delete Data"])

if select_option == "Insert Data":
    st.sidebar.title("Upload Option")
    insert_data()
    

elif select_option == "Update Data":
    st.sidebar.title("Update Data")
    company_name = st.sidebar.text_input("Company Name")

    # Button for each field
    if company_name:
        st.sidebar.write("Select Field to Update:")
        selected_field = st.sidebar.selectbox("", ["Company Name", "Card Holder", "Designation", "Mobile Number", "Email", "Website", "Area", "City", "State", "Pin Code"])

        new_value = None
        if selected_field:
            new_value = st.sidebar.text_input(f"New {selected_field}")
        
        if st.sidebar.button("Update"):
            if new_value is not None:
                update_data(company_name, selected_field.replace(" ", "_").lower(), new_value)
            else:
                st.warning("Please provide a new value.")

elif select_option == "Fetch Updated Data":
    st.sidebar.title("Fetch Updated Data")
    company_name = st.sidebar.text_input("Company Name")
    if st.sidebar.button("Fetch"):
        if company_name:
            updated_data = fetch_updated_data(company_name)
            if updated_data:
                st.write("Updated Data:")
                st.table([updated_data])  # Wrap the data in a list before passing it to st.table()
            else:
                st.warning("Company name not found in the database.")
        else:
            st.warning("Please enter a company name.")

elif select_option == "Delete Data":
    st.sidebar.title("Delete Data")
    company_name_to_delete = st.sidebar.text_input("Company Name to Delete")
    if st.sidebar.button("Delete"):
        if company_name_to_delete:
            delete_data(company_name_to_delete)
        else:
            st.warning("Please enter a company name to delete.")

# Close the cursor and MySQL connection
try:
    if cursor.with_rows:
        cursor.fetchall()  # Consume any pending results
except mysql.connector.Error as err:
    st.error(f"Error fetching remaining results: {err}")
cursor.close()
mysql_conn.close()
