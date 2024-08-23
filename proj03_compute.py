#
# Python program to open and process a PDF file, extracting
# all numeric values from the document. The goal is to tally
# the first significant (non-zero) digit of each numeric
# value, and save the results to a text file. This will
# allow checking to see if the results follow Benford's Law,
# a common method for detecting fraud in numeric data.
#
# https://en.wikipedia.org/wiki/Benford%27s_law
# https://chance.amstat.org/2021/04/benfords-law/
#

import json
import boto3
import os
import uuid
import base64
import pathlib
import datatier
import urllib.parse
import string

from configparser import ConfigParser
from pypdf import PdfReader

def lambda_handler(event, context):
  try:
    print("**STARTING**")
    print("**lambda: proj03_compute**")

    # 
    # in case we get an exception, initial this filename
    # so we can write an error message if need be:
    #
    bucketkey_results_file = ""

    #
    # setup AWS based on config file:
    #
    config_file = 'benfordapp-config.ini'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file

    configur = ConfigParser()
    configur.read(config_file)

    #
    # configure for S3 access:
    #
    s3_profile = 's3readwrite'
    boto3.setup_default_session(profile_name=s3_profile)

    bucketname = configur.get('s3', 'bucket_name')

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketname)

    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')

    #
    # this function is event-driven by a PDF being
    # dropped into S3. The bucket key is sent to 
    # us and obtain as follows:
    #
    bucketkey = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    print("bucketkey:", bucketkey)

    extension = pathlib.Path(bucketkey).suffix

    if extension != ".pdf" : 
      raise Exception("expecting S3 document to have .pdf extension")

    bucketkey_results_file = bucketkey[0:-4] + ".txt"

    print("bucketkey results file:", bucketkey_results_file)

    #
    # download PDF from S3 to LOCAL file system:
    #
    print("**DOWNLOADING '", bucketkey, "'**")

    #
    # TODO #1 of 8: where do we write local files? Replace
    # the ??? with the local directory where we have access.
    #
    local_pdf = "/tmp/data.pdf"

    bucket.download_file(bucketkey, local_pdf)

    #
    # open LOCAL pdf file:
    #
    print("**PROCESSING local PDF**")

    reader = PdfReader(local_pdf)
    number_of_pages = len(reader.pages)

    #
    # TODO #2 of 8: update status column in DB for this job,
    # change the value to "processing - starting". Use the
    # bucketkey --- stored as datafilekey in the table ---
    # to identify the row to update. Use the datatier.
    #
    # open connection to the database:
    #
    #print("**Opening DB connection**")
    #
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    #
    # ???
    #

    sql = "select jobtype from jobs where datafilekey =%s;"
    jobtype = datatier.retrieve_one_row(dbConn, sql, [bucketkey])[0]

    sql = "update jobs set status=%s where datafilekey=%s;"
    datatier.perform_action(dbConn, sql, ["processing - starting", bucketkey])


    local_results_file = "/tmp/results.txt"

    outfile = open(local_results_file, "w")

    #
    # for each page, extract text, split into words,
    # and see which words are numeric values:
    #
    comprehend = boto3.client(service_name='comprehend', region_name='us-east-2')
    if jobtype == "sentiment":
      # text = ""
      # for i in range(0, number_of_pages):
      #   page = reader.pages[i]
      #   text = text + page.extract_text()
      text = reader.pages[0].extract_text()
      words = text.split()
      res = ""
      for word in words:
        res += word + " "

      outfile.write("**RESULTS**\n")
      outfile.write("**Sentiment Analysis**\n")

      comprehend_json_obj = comprehend.detect_sentiment(Text = text, LanguageCode= 'en')
      json_text = json.dumps(comprehend_json_obj, indent=4)
      print("json_text:", json_text)
      sentiment = comprehend_json_obj['Sentiment']

      outfile.write("Sentiment: " + sentiment + "\n")

      scores = comprehend_json_obj['SentimentScore']
      outfile.write("Sentiment scores:" + "\n")
      outfile.write("Positive: " + str(scores["Positive"]) + "\n")
      outfile.write("Negative: " + str(scores["Negative"]) + "\n")
      outfile.write("Neutral: " + str(scores["Neutral"]) + "\n")
      outfile.write("Mixed: " + str(scores["Mixed"]) + "\n")

      outfile.close()



      ## run from here, text = full block. 

    elif jobtype == "ner":
      text = ""
      for i in range(0, number_of_pages):
        page = reader.pages[i]
        text = text + page.extract_text()

      ## run analysis here



      ## only take entities above certain threshold?

      outfile.write("**RESULTS**\n")
      outfile.write("**Name Entity Recognition**\n")

      ## run from here, text = full block. 
      comprehend_json_obj = comprehend.detect_entities(Text = text, LanguageCode= 'en')
      json_text = json.dumps(comprehend_json_obj, indent=4)
      print("json_text:", json_text)
      entities = comprehend_json_obj['Entities']
      for entity in entities:
        outfile.write("Type: " + entity["Type"] + "\n")
        outfile.write("Text: " + entity["Text"] + "\n")
        outfile.write("Score: " + str(entity["Score"]) + "\n\n")
      
      outfile.close()
      

    elif jobtype == "pii":
      text = ""
      for i in range(0, number_of_pages):
        page = reader.pages[i]
        text = text + page.extract_text()

      outfile.write("**RESULTS**\n")
      outfile.write("**Personally Identifiable Entities**\n")

      ## run from here, text = full block.  
      comprehend_json_obj = comprehend.detect_pii_entities(Text = text, LanguageCode= 'en')
      json_text = json.dumps(comprehend_json_obj, indent=4)
      print("json_text:", json_text)
      entities = comprehend_json_obj['Entities']
      for entity in entities:
        outfile.write("Type: " + entity["Type"] + "\n")
        outfile.write("Score: " + str(entity["Score"]) + "\n\n")
        
      outfile.close()
      
    else:
      digits = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '7': 0, '8': 0, '9': 0}
      for i in range(0, number_of_pages):
        page = reader.pages[i]
        text = page.extract_text()
        words = text.split()
        print("** Page", i+1, ", text length", len(text), ", num words", len(words))
        for word in words:
          word = word.translate(str.maketrans('', '', string.punctuation))
          if word.isnumeric():
            #
            # find the first non-zero digit and count it:
            #
            # TODO #3 of 8: add code to do the counting of digits 1..9
            #
            # ???
            #
            for d in word:
              if d is not '0':
                dig = d
                digits[dig] += 1
                break
        #
        # now that page has been processed, let's update database to
        # show progress...
        #
        # TODO #4 of 8: update status column in DB for this job,
        # change the value to "processing - page x of y completed".
        # Use the bucketkey --- stored as datafilekey in table ---
        # to identify the row to update. Use the datatier.
        #
        # ???
        #
        sql = "update jobs set status=%s where datafilekey=%s;"
        stat = "processing - page " + str(i) + " of " + str(number_of_pages) + " completed"
        datatier.perform_action(dbConn, sql, [stat, bucketkey])


      #
      # analysis complete, write the results to local results file:
      #
      # TODO #5 of 8: where do we write local files? Replace
      # the ??? with the local directory where we have access.
      #

      outfile.write("**RESULTS**\n")
      outfile.write("**Benford Analysis**\n")
      outfile.write(str(number_of_pages))
      outfile.write(" pages\n")

      #
      # TODO #6 of 8: Write the 10 counts to the file:
      #
      # ???
      #

      outfile.write("0 0\n")

      for d in digits.keys():
        outfile.write(str(d) + " " + str(digits[d]) + "\n")

      outfile.close()

    #
    # upload the results file to S3:
    #
    print("**UPLOADING to S3 file", bucketkey_results_file, "**")

    bucket.upload_file(local_results_file,
                       bucketkey_results_file,
                       ExtraArgs={
                         'ACL': 'public-read',
                         'ContentType': 'text/plain'
                       })

    # 
    # The last step is to update the database to change
    # the status of this job, and store the results
    # bucketkey for download:
    #
    # TODO #7 of 8: update both the status column and the 
    # resultsfilekey for this job in the DB. The job is 
    # identified by the bucketkey --- datafilekey in the 
    # table. Change the status to "completed", and set
    # resultsfilekey to the contents of your variable
    # bucketkey_results_file.
    #
    # ???
    #
    sql = "update jobs set status=%s where datafilekey=%s;"
    datatier.perform_action(dbConn, sql, ["completed", bucketkey])
    sql = "update jobs set resultsfilekey=%s where datafilekey=%s;"
    datatier.perform_action(dbConn, sql, [bucketkey_results_file, bucketkey])


    #
    # done!
    #
    # respond in an HTTP-like way, i.e. with a status
    # code and body in JSON format:
    #
    print("**DONE, returning success**")

    return {
      'statusCode': 200,
      'body': json.dumps("success")
    }

  #
  # on an error, try to upload error message to S3:
  #
  except Exception as err:
    print("**ERROR**")
    print(str(err))

    local_results_file = "/tmp/results.txt"
    outfile = open(local_results_file, "w")

    outfile.write(str(err))
    outfile.write("\n")
    outfile.close()

    if bucketkey_results_file == "": 
      #
      # we can't upload the error file:
      #
      pass
    else:
      # 
      # upload the error file to S3
      #
      print("**UPLOADING**")
      #
      bucket.upload_file(local_results_file,
                         bucketkey_results_file,
                         ExtraArgs={
                           'ACL': 'public-read',
                           'ContentType': 'text/plain'
                         })

    #
    # update jobs row in database:
    #
    # TODO #8 of 8: open connection, update job in database
    # to reflect that an error has occurred. The job is 
    # identified by the bucketkey --- datafilekey in the 
    # table. Set the status column to 'error' and set the
    # resultsfilekey column to the contents of the variable
    # bucketkey_results_file.
    #
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    #
    # ???
    #
    sql = "update jobs set status=%s where datafilekey=%s;"
    datatier.perform_action(dbConn, sql, ["error", bucketkey])
    sql = "update jobs set resultsfilekey=%s where datafilekey=%s;"
    datatier.perform_action(dbConn, sql, [bucketkey_results_file, bucketkey])

    #
    # done, return:
    #    
    return {
      'statusCode': 400,
      'body': json.dumps(str(err))
    }
