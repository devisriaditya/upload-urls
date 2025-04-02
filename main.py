import xmlrpc.client
import os
from dotenv import load_dotenv
import requests
from google.cloud import storage

load_dotenv()

# Odoo connection setup
url = 'http://localhost:8010'
db = 'new_one'
username = 'admin'
password = 'Sriveni@1'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Fetch PDF URLs (limit=2)
report_pdf_urls = models.execute_kw(
    db, uid, password, 'certificate.data', 'search_read',
    [[]],  # Empty domain to fetch all records
    {'fields': ['report_pdf_api_url']}  # Get 2 records
)


def get_gcs_bucket():
    """Get GCS bucket object and name."""
    bucket_name = os.getenv("GCP_BUCKET_NAME")
    credentials_path = os.getenv('GCS_CREDENTIALS_PATH',
                                 '/home/adi/Desktop/jenkins/static/data/sim-gems-videos-e8e3607d0460.json')

    if not credentials_path or not bucket_name:
        raise ValueError("GCS credentials or bucket name not configured!")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    return bucket, bucket_name


def upload_pdf_to_gcs(pdf_url, filename):
    """Upload a single PDF to GCS and return its public URL."""
    try:
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', 'application/pdf')
        if 'pdf' not in content_type.lower():
            print(f"Warning: Unexpected content type: {content_type}")

        bucket, bucket_name = get_gcs_bucket()
        blob = bucket.blob(f"{filename}.pdf")
        blob.upload_from_string(response.content, content_type=content_type)

        gcs_url = f"https://storage.googleapis.com/{bucket_name}/{filename}.pdf"
        print(f"Uploaded PDF to GCS: {gcs_url}")
        return gcs_url
    except Exception as e:
        print(f"Failed to upload {pdf_url}: {e}")
        return None


# Extract PDF URLs
pdf_api_urls = [record['report_pdf_api_url'] for record in report_pdf_urls if record.get('report_pdf_api_url')]

# Upload each PDF with a unique filename
if pdf_api_urls:
    for i, pdf_url in enumerate(pdf_api_urls, 1):
        filename = f"pdf_report_{i}"  # Unique filename for each PDF
        uploaded_url = upload_pdf_to_gcs(pdf_url, filename)
        if uploaded_url:
            print(f"Successfully uploaded: {uploaded_url}")
else:
    print("No report PDF URLs found.")