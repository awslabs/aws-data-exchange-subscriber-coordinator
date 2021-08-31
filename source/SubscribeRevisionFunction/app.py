#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                         
##############################################################################

import json
import boto3
import os
import logging
from datetime import datetime
import urllib3

def lambda_handler(event, context):

    try:
        global log_level
        log_level = str(os.environ.get('LOG_LEVEL')).upper()
        if log_level not in [
                                'DEBUG', 'INFO',
                                'WARNING', 'ERROR',
                                'CRITICAL'
                            ]:
            log_level = 'ERROR'
        logging.getLogger().setLevel(log_level)

        logging.debug('event={}'.format(event))
        datasetId = event['resources'][0]
        revisionId = event['detail']['RevisionIds'][0]
        bucket = os.environ['BUCKET']
        prefix_start = os.environ['PREFIX_START']
        prefix = prefix_start + '/' + datasetId + '/' + revisionId 
        dataexchange = boto3.client(service_name='dataexchange')
        assetlist = dataexchange.list_revision_assets(DataSetId=datasetId,RevisionId=revisionId)
        assets = []
        for asset in assetlist['Assets']:
            assetId = asset['Id']
            nameparts = asset['Name'].split('/')
            filename = nameparts[len(nameparts)-1]
            assets.append({
                  "AssetId": assetId,
                  "Bucket": bucket,
                  "Key": prefix + '/' + filename
                })

        revisiondetails = {
            "ExportAssetsToS3": {
                "AssetDestinations": 
                    assets 
                ,
                "DataSetId": datasetId,
                "RevisionId": revisionId
            }
        }

        logging.debug('revisiondetails={}'.format(revisiondetails))
        jobresponse = dataexchange.create_job(Type='EXPORT_ASSETS_TO_S3', Details=revisiondetails)
        jobArnparts = jobresponse['Arn'].split('/')
        jobId = jobArnparts[1]
        logging.info('jobId={}'.format(jobId))
        startjobresponse = dataexchange.start_job(JobId=jobId)
        sendMetrics=os.environ.get('AnonymousUsage')
        if sendMetrics=="Yes":
            metricdata = {
                "Version" : os.environ.get('Version'),
                "AssetCount" : len(assetlist)
            }
            solutionData={
                "Solution": os.environ.get('SolutionId'),
                "UUID": os.environ.get('UUID'),
                "TimeStamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
                "Data": metricdata
            }
            http = urllib3.PoolManager()
            metricURL = "https://metrics.awssolutionsbuilder.com/generic"
            encoded_data = json.dumps(solutionData).encode('utf-8')
            headers={'Content-Type': 'application/json'}
            http.request('POST',metricURL,
                                body=encoded_data,
                                headers=headers)
    except Exception as e:
        logging.error(e)
        raise e
    return {
        "Message": "Subscription Started",
        "DataSetId": datasetId,
        "RevisionId": revisionId,
        "JobId": jobId,
        "JobStatus" : "IN_PROGRESS"
    }
