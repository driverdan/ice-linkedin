import time
import json
import csv
import os
import requests
from bs4 import BeautifulSoup
from jinja2 import Template
import headers

FUNCTION_FACETS = [
    17,
    18,
    14,
    2,
    4,
    20,
    5,
    13,
    12,
    26,
]

def download_file(url, local_filename=None):
    if local_filename is None:
        local_filename = url.split('/')[-1]

    print('saving to', local_filename)
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return local_filename


def get_page(company_id, function_id, start=0, count=50):
    # facet.FA	17
    params = {
        'facet': ['CC', 'FA'],
        'facet.CC': company_id,
        'facet.FA': function_id,
        'count': count,
        'start': start,
    }

    response = requests.get('https://www.linkedin.com/sales/search/results', headers=headers.headers, params=params)
    return response.json()


def get_company(company_id, outname):
    people = []

    for function_id in FUNCTION_FACETS:
        print('getting function', function_id, 'for company', company_id)
        count = 50
        start = 0
        results = get_page(company_id, function_id)
        total = results['pagination']['total']
        people += results['searchResults']
        start += count
        while start < total:
            print('getting', start, 'of', total)
            time.sleep(1)
            results = get_page(company_id, function_id, start)
            people += results['searchResults']
            start += count

            with open(outname, 'w') as outfile:
                json.dump(people, outfile, indent=2)

    return outname


def get_images(datafile):
    with open(datafile, 'r') as infile:
        people = json.load(infile)

    people = [p['member'] for p in people]

    for p in people:
        if 'vectorImage' not in p:
            continue

        pid = p['memberId']
        outname = 'images/{}.jpg'.format(pid)

        if os.path.exists(outname):
            print('skipping')
            continue

        url = p['vectorImage']['rootUrl']
        url += sorted(p['vectorImage']['artifacts'], key=lambda x: x['width'])[-1]['fileIdentifyingUrlPathSegment']

        print(url)

        download_file(url, outname)

        time.sleep(1)


def get_profile(pid):
    outname = 'profiles/{}.json'.format(pid)
    if os.path.exists(outname):
        return outname

    out = {}
    url = 'https://www.linkedin.com/sales/people/{},NAME_SEARCH'.format(pid)
    print(url)
    response = requests.get(url, headers=headers.headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    codes = soup.select('code')
    for c in codes:
        try:
            d = json.loads(c.text)
            if 'contactInfo' in d:
                out = d
                break
        except Exception as e:
            continue

    with open(outname, 'w') as outfile:
        json.dump(out, outfile)

    time.sleep(1)
    return outname


def get_profiles(datafile):
    with open(datafile, 'r') as infile:
        data = json.load(infile)

    for d in data:
        pid = d['member']['profileId']
        get_profile(pid)


def clean_and_parse(datafile, outname):
    out = []
    with open(datafile, 'r') as infile:
        data = json.load(infile)

    for d in data:
        mid = d['member']['memberId']
        pid = d['member']['profileId']

        imgpath = 'images/{}.jpg'.format(mid)
        if not os.path.exists(imgpath):
            imgpath = None

        item = {
            'name': d['member'].get('formattedName', ''),
            'title': d['member'].get('title', ''),
            'img': imgpath,
            'company': d['company'].get('companyName', ''),
            'location': d['member'].get('location', ''),
            'id': d['member']['memberId'],
            'linkedin': 'https://linkedin.com/in/' + pid,
        }

        # profile_file = 'profiles/{}.json'.format(pid)
        # if os.path.exists(profile_file):
        #     with open(profile_file, 'r') as profilein:
        #         profile = json.load(profilein)

        if mid not in out:
            out.append(item)

    with open(outname + '.json', 'w') as jsonfile:
        json.dump(out, jsonfile, indent=2)

    with open(outname + '.csv', 'w') as csvfile:
        fieldnames = list(out[0].keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in out:
            writer.writerow(row)

    with open('template.html', 'r') as templatefile:
        template = Template(templatefile.read())
    html = template.render(people=out)
    with open('index.html', 'w') as htmlout:
        htmlout.write(html)


if __name__ == '__main__':
    ICE = '533534'
    datafile = 'ice_raw.json'
    get_company(ICE, datafile)
    get_profiles(datafile)
    get_images(datafile)
    clean_and_parse(datafile, 'ice')
