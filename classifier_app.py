import streamlit as st
import requests
from bs4 import BeautifulSoup
from google.cloud import language_v1 as gc
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account
from annotated_text import annotated_text

"""
# Brand Safety Classifier
Add a URL and set parameters to run the demo classifier. The text model is based on the Google Clound NL API and Brand Safety Classifier.
"""

# Get user inputs
URL = 'https://www.theguardian.com/commentisfree/joris-luyendijk-banking-blog/2011/nov/09/goldman-sachs-elevator-gossip-tweets'
Text = 'The small plane carrying a pilot and two passengers was travelling north over Haulover Inlet Bridge when it crashed into an SUV travelling southbound, Miami-Dade police said in a press release. The plane then caught fire and fire officials discovered a body in the plane while extinguishing the flames.'

input_API = st.selectbox(
     'Select the API: ',
     ['Natural Language API','Content Moderation API']
     )

# Show option based on user selection 

if input_API == 'Natural Language API':
     input_NL_category = st.selectbox(
          '[Cloud NL API] Which categories should be flagged?',
          ['None', 'Sensitive Subjects', 'Adult', 'Health']
          )
     input_type = st.radio(
     "Select Input ",
     ('URL', 'Free Text'))

     uploaded_file = None
else:
     input_type = st.radio(
     "Select Input ",
     ('URL', 'Free Text', 'PNG File'))

# Show input fields based on user selection 

if input_type == 'Free Text':
     uploaded_file = None
     input_text = st.text_area("Insert Free Text", Text ) 
     text_content = input_text
elif input_type == 'URL':
     uploaded_file = None          
     input = st.text_area("Insert URL", URL)
     #text_content variable will be assigned after parsing paragraphs
elif input_type == 'PNG File':     
     uploaded_file = st.file_uploader("Choose a file")
     if uploaded_file is not None:
          # To read file as bytes:
          text_content = uploaded_file.getvalue()
     else:
          pass
     
 # Set threshold
input_threshold = st.slider(label="Set confidence threshold", min_value=0.1, max_value=1.0, value=0.7, step=.1)


# Define the NL API function
def classify_text(text_content):
    """
    Classifying Content in a String

    Args:
      text_content The text content to analyze. Must include at least 20 words.
    """

    credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
    )
    client = gc.LanguageServiceClient(credentials=credentials)
 


    # Available types: PLAIN_TEXT, HTML
    type_ = gc.Document.Type.PLAIN_TEXT

    language = "en"
    document = {"content": text_content, "type_": type_, "language": language}

    response = client.classify_text(request = {'document': document})
    
    # Define the brand safety signal, and assume safe unless indicated otherise:
    signal = 'brand safe'
     
    # Loop through classified categories returned from the API
    for category in response.categories:
          
        #st.write(u"Category name: {}".format(category.name))
        #st.write(u"Confidence: {}".format(category.confidence))
          
        if input_NL_category in category.name and category.confidence >= input_threshold and signal == 'brand safe':
            signal = 'brand unsafe'
               
            # Note that the following output only details the first category and confidence that affects the brand safety flag   
            st.write(u"Category name: {}".format(category.name))
            st.write(u"Confidence: {}".format(category.confidence))   
          
    return signal


def moderate_content(text_content):
     project_id= '514252618350'
     location = 'us'
     processor_id = '941d43789dae7e98'
     credentials = service_account.Credentials.from_service_account_info(
     st.secrets["gcp_service_account"]
     )

     opts = {"api_endpoint": f"{location}-documentai.googleapis.com"}

     if location == "eu":
         opts = {"api_endpoint": "eu-documentai.googleapis.com"}

     client = documentai.DocumentProcessorServiceClient(client_options=opts, credentials=credentials)

     name = client.processor_path(project_id, location, processor_id)

     if uploaded_file is not None:
          document = documentai.RawDocument(content=text_content, mime_type='image/png')
          request = documentai.ProcessRequest(name=name, raw_document=document)
     else:
          document = documentai.Document(text=text_content, mime_type='plain/text')
          request = documentai.ProcessRequest(name=name, inline_document=document)

     # Send request
     result = client.process_document(request=request)
     document = result.document
     
     
     # Define the brand safety signal, and assume safe unless indicated otherise:
     signal = 'brand safe'

     for entity in document.entities:
         if entity.confidence >= input_threshold and signal == 'brand safe':
             signal = 'brand unsafe'
             # Note that the following output only details the first category and confidence that affects the brand safety flag   
             st.write(u"Category name: {}".format(entity.type_))
             st.write(u"Confidence: {}".format(entity.confidence))
     
     if uploaded_file is not None:
          st.write(document.text)
          OCR = document.text
          if signal == 'brand unsafe':
               background = "#faa"
          else:
              background = "#dcdcdc"
              annotated_text(
              (OCR, signal, background),
              )
     else:
          OCR = ''
         
     return signal

# If upload detected, run the content moderation without URL scraping
if uploaded_file is not None:
     signal = moderate_content(text_content = text_content) 

# If free text is detected, run the content moderation without URL scraping     
elif input_type == 'Free Text':
   text_content = input_text
   if input_API == 'Natural Language API':
     signal = classify_text(text_content = text_content)
   else:       
     signal = moderate_content(text_content = text_content)   
   if signal == 'brand unsafe':
     background = "#faa"
   else:
     background = "#dcdcdc"
   annotated_text(
   (text_content, signal, background),
   )

# Scrape URL and run classifier
elif input_type == 'URL': 
     # Take URL input and parse
     URL = input
     page = requests.get(URL)
     soup = BeautifulSoup(page.content, "html.parser")
     
     # Run classifier
     i=0
     for para in soup.find_all("p"):
          if(len(str(para)) > 120):
             st.write("paragraph #",str(i))
             text_content = para.get_text()
             if input_API == 'Natural Language API':
               signal = classify_text(text_content = text_content)
             else:       
               signal = moderate_content(text_content = text_content)   
             if signal == 'brand unsafe':
               background = "#faa"
             else:
               background = "#dcdcdc"
             annotated_text(
             (text_content, signal, background),
             )
             st.markdown("""---""")
             i+=1
        
