import json
import requests
from collections import defaultdict
from datetime import datetime


def get_data(iso3, start_date, end_date):
    url = f'https://api.hungermapdata.org/v1/foodsecurity/country/{iso3}/region?date_start={start_date}&date_end={end_date}'
    response = requests.get(url)
    response_json = response.json()
    return response_json


def organize_by_admin1(raw_arr):
    out = {}
    for d in raw_arr:
        out.setdefault(d['region']['id'], []).append({'region': d['region'],
                                                      'date': d['date'],
                                                      'metrics': d["metrics"]})
    return out

def organize_by_date(raw_arr, key_name):
    output = defaultdict(lambda: [])
    for item in raw_arr:
        output[item[key_name]].append(item)
    return output

def calculate_average(raw_arr, key_name):
    def str_to_date(str_date):
        date_obj = datetime.strptime(str_date, '%Y-%m-%d')
        return f'{date_obj.year}-{date_obj.month}'

    output = defaultdict(lambda: [])
    for v in raw_arr:
        output[str_to_date(v[key_name])].append(v['metrics']['fcs'])

    average = {}
    for k, v in output.items():
        average[k] = {
            'people': (sum(c['people'] for c in v)) / len(v),
            'prevalence': (sum(c['prevalence'] for c in v)) / len(v)
        }

    return average

def calculate_adm1_monthly_average(iso3, start_date, end_date):
    raw_data = get_data(iso3, start_date, end_date)
    adm1_data = organize_by_admin1(raw_data)
    out = []
    for k, v in adm1_data.items():
        out.append({
            'region': v[0]['region'],
            'average': calculate_average(v, 'date')
        })
    return out

def calculate_national_estimate(raw_data):
    total_people = 0
    weighted_prevalence_sum = 0

    for region_data in raw_data:
        metrics = region_data['metrics']
        people = metrics['fcs']['people']
        prevalence = metrics['fcs']['prevalence']

        total_people += people
        weighted_prevalence_sum += people * prevalence

    national_prevalence_estimate = weighted_prevalence_sum / total_people

    return total_people, national_prevalence_estimate

def calculate_national_estimate_variance(raw_data, national_prevalence_estimate):
    num_regions = len(raw_data)
    squared_diff_sum = 0

    for region_data in raw_data:
        metrics = region_data['metrics']
        prevalence = metrics['fcs']['prevalence']
        squared_diff_sum += (prevalence - national_prevalence_estimate) ** 2

    variance = squared_diff_sum / num_regions

    return variance

def calculate_daily_national_estimate(iso3, start_date, end_date):
    try:
        raw_data = get_data(iso3, start_date, end_date)
        date_key = organize_by_date(raw_data, 'date')
        data = {}
        for k, v in date_key.items():
            tot_people, national_esitmate = calculate_national_estimate(v)
            variance = calculate_national_estimate_variance(v, national_esitmate)
            data[k] = {
                'people': tot_people,
                'prevalence': national_esitmate,
                'variance': variance
            }
        return data
    except:
        return

def get_estimated_data(iso3):
    try:
        return calculate_daily_national_estimate(iso3, '2022-06-01', '2023-06-01')
    except:
        with open('last_calculated_data.json', 'r') as f:
            data = json.load(f)
            return data[iso3]

def lambda_handler(event, context):
    COL_data = get_estimated_data('COL')
    BFA_data = get_estimated_data('BFA')
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(
            {
             'COL': COL_data,
             'BFA': BFA_data
            }
        )
    }

print(lambda_handler(None,None))