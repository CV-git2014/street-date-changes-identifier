import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import streamlit as st

#--------------------------------------
#Creating a sidebar for different tasks
#--------------------------------------
side = st.sidebar
side.title('Select the task you want to complete.')
side_selector = side.radio('Select one:', options=['Home','Update Street Dates'])

#------------------
#Creating Home Page
#------------------
if side_selector == 'Home':
    st.title("Welcome to the Comeback Vinyl Task Automater")
    st.markdown("**The purpose of this app is to provide a centralized and easy to use tool to complete repettive tasks.:thumbsup:**")
    st.markdown('Navigate to the sidebar menu and select the task you wish to complete. Further instructions for each task are located on the associated page.')


#------------------------------
#------------------------------
#Code for updating Street Dates
#------------------------------
#------------------------------
if side_selector == 'Update Street Dates':

    #creating Title, description, and the drop box fields
    st.title('Update Street Dates Application')
    st.markdown("**__This app checks street dates for input files and returns only items that need to be updated or double checked.__**:ok_hand:")
    st.markdown('**__IMPORTANT NOTE:__** All files need to be formatted as .xlsx')
    alliance = st.file_uploader(label='Drop the Allinace.xlsx file here',type='xlsx')
    end_cap = st.file_uploader(label='Drop the End_Cap.xlsx here', type='xlsx')


    if alliance is not None and end_cap is not None:
        #Reading and cleaning functions for each dataframe
        def clean_alliance(alliance):
            alliance_df  = pd.read_excel(alliance, skiprows=10)
            alliance_df.drop([0], inplace=True)
            alliance_df.drop(['Product', 'Qty', 'Adj', 'Sell','Adj.1','Spcl','Non','Media','CutOut', 'Last Return','BO','Num'], axis = "columns", inplace = True)
            alliance_df.UPC = alliance_df.UPC.astype(int)
            return alliance_df
        alliance_df = clean_alliance(alliance)

        def clean_endcap(end_cap):
            endcap_df_og = pd.read_excel(end_cap)
            endcap_df_og['UPC'] = pd.to_numeric(endcap_df_og['UPC'])
            endcap_df_og = endcap_df_og[endcap_df_og['UPC'].notna()]
            endcap_df_og['UPC'] = endcap_df_og['UPC'].astype(int)
            endcap_df = endcap_df_og
            return endcap_df
        endcap_df = clean_endcap(end_cap) 

        today = datetime.now()
        #Merging the two dfs so that date comparions can be made.
        def outer_merged_df(df_1, df_2):
            updated_df = pd.merge(df_1, df_2,  on = 'UPC', how = 'outer')
            updated_df['Date Compare'] = (updated_df['Street Date On Site (1/1/21 means TBA)'] == updated_df['Street'])
            
            #-----------------------------------------------------------------------------------
            #Trimming down to only have items that are yet to be released and need updated dates
            #-----------------------------------------------------------------------------------
            

            updated_df['Past Street Date'] = (updated_df['Street Date On Site (1/1/21 means TBA)'] < today)

            final_updated_df = updated_df[updated_df['Past Street Date'] == False]
            final_updated_df = final_updated_df[final_updated_df['Date Compare'] == False]
            final_updated_df.drop(['Artist','Title_x','Date(s) Ordered','Notes','List','Qty','First Time Ordering?','Date Compare','Past Street Date'], axis = 'columns' , inplace=True)
            final_updated_df['Title_y'] = final_updated_df['Title_y'].str.title().str.rstrip().str.replace('"', '')
            
            return final_updated_df
        final_updated_df = outer_merged_df(alliance_df, endcap_df)



        #Function for web scraper
        def rsdessentials_scraper():
            rsd_url  = 'https://www.rsdessentials.com/streetdates'
            headers = {"Accept-Language": "en-US, eb;q=0.5"} #Scrapes english translated items
            results = requests.get(rsd_url, headers=headers)
            content = BeautifulSoup(results.text, 'html.parser')
            rsd_div = content.find_all('div', class_='list-item-content')
            #-------------------------------------------------------------------
            #Looping through the web scrapped data to get only the things needed
            #-------------------------------------------------------------------
            title = []
            dscrp = []
            for container in rsd_div:
                name = container.h2.text
                title.append(name)    
                description = container.p.text
                dscrp.append(description)
            #--------------------------------------------------
            #Putting the two seperate lists in to one Pandas DF
            #--------------------------------------------------

            think_indie_df = pd.DataFrame({
                                'Title': title,
                                'release_street_date': dscrp
            })
            #-------------------------------------------------------
            #Stripping off unintentional spaces and extracting dates 
            #-------------------------------------------------------
            think_indie_df['release_street_date'] = think_indie_df['release_street_date'].str.rstrip()
            st.write(think_indie_df)
            think_indie_df[['Description', 'Release/Street Date']] = think_indie_df['release_street_date'].str.rsplit(pat=' ', n=1, expand = True)
            think_indie_df = think_indie_df[think_indie_df['Release/Street Date'] != 'TBD']
            think_indie_df['Release/Street Date'] = pd.to_datetime(think_indie_df['Release/Street Date'])
            think_indie_df = think_indie_df[think_indie_df['Release/Street Date'] > today]
            
            #-----------------------------------------------
            #Creating a subset df of only Think Indie titles
            #-----------------------------------------------
            ti_subset_df = (final_updated_df[final_updated_df['Vendor'] == 'think indie'])
            ti_subset_df = ti_subset_df.loc[ti_subset_df['On The Site?'] != 'EMBARGO']
            if not ti_subset_df.empty:
                ti_subset_df[['Title','msc1', 'msc2']] = ti_subset_df['Title_y'].str.rsplit(pat=' ', n=2, expand = True)
                ti_subset_df.drop(['Title_y', 'msc1', 'msc2'],axis = 'columns', inplace = True)
            else:
                ti_subset_df.rename(columns={'Title_y': "Title"}, inplace=True)
            #---------------------------------------------------------------
            #Merge web data with our think indie data from the end cap sheet
            #---------------------------------------------------------------
            ti_subset_df = pd.merge(ti_subset_df, think_indie_df,  on = 'Title', how = 'left')
            ti_subset_df['Date Compare'] = (ti_subset_df['Street Date On Site (1/1/21 means TBA)'] == ti_subset_df['Release/Street Date'])
            ti_subset_df = ti_subset_df[ti_subset_df['Date Compare'] == False]
            return ti_subset_df


        #Last things to clean up before the appending the TI data
        if not final_updated_df.empty:
            ti_subset_df = rsdessentials_scraper()

            final_updated_df.drop_duplicates(subset = ['UPC'], inplace = True)
            final_updated_df = final_updated_df[final_updated_df['Vendor'] != 'think indie'] 
            final_updated_df.rename(columns = {'Title_y' : 'Title'}, inplace = True)
            final_updated_df = final_updated_df.append(ti_subset_df, ignore_index = True)
            final_updated_df.drop(['Mock-Up Made?','On The Site?', 'release_street_date', 'Date Compare', 'Description'],axis = 'columns', inplace = True)
            final_updated_df.rename(columns = {'Street' : 'Updated Street Date From Alliance', 'Release/Street Date' : 'Updated Date From TI', 'Street Date On Site (1/1/21 means TBA)' : 'Old Street Date'}, inplace = True)
            final_updated_df['Updated Street Date From Alliance'] = pd.to_datetime(final_updated_df['Updated Street Date From Alliance']).dt.date
            final_updated_df['Old Street Date'] = pd.to_datetime(final_updated_df['Old Street Date']).dt.date
            @st.cache
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8')
            
            csv = convert_df(final_updated_df)
            st.table(final_updated_df)
            st.download_button(
                label='Download as CSV',
                data = csv,
                file_name = 'updated_street_dates.csv',
                )
