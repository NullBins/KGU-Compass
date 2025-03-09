from flask import Flask, render_template, jsonify, request
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from pymongo import MongoClient

app = Flask(__name__)

uri = "DB_URI"
connect = MongoClient(uri, 27017)
db = connect.kgdb

def parse_date(date_str):
    pattern = r'(\d{4})\.(\d{2})\.(\d{2})'
    dates = re.findall(pattern, date_str)
    if dates:
        start_date = f"{dates[0][0]}-{dates[0][1]}-{dates[0][2]}"
        if len(dates) > 1:
            end_date = f"{dates[1][0]}-{dates[1][1]}-{dates[1][2]}"
        else:
            end_date = start_date
        return start_date, end_date
    return None, None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/infoPage')
def info():
    return render_template('infoPage.html')

@app.route('/notice', methods=['GET', 'POST'])
def get_notice():
    uri = 'https://www.kyonggi.ac.kr/www/selectBbsNttList.do?key=5133&bbsNo=680'
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(uri, headers=headers)
    data.encoding = 'utf-8'
    soup = BeautifulSoup(data.text, 'html.parser')
    notices = soup.select('.p-media--gallery > .p-media-list > .p-media')
    if notices:
        recent_notice = notices[0]
        title_element = recent_notice.select_one('.p-media__heading-text')
        if title_element:
            title_name = title_element.get_text(strip=True)
    doc = {
        "title_name": title_name
    }
    db.notice.delete_many({})
    db.notice.insert_one(doc)
    return jsonify({'result':'success'})

@app.route('/plan', methods=['GET', 'POST'])
def get_plan():
    uri = 'https://www.kyonggi.ac.kr/www/selectTnSchafsSchdulListUS.do?key=5695&sc1=10'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(uri, headers=headers)
    data.encoding = 'utf-8'
    soup = BeautifulSoup(data.text, 'html.parser')
    plans = soup.select('.panel_half.even')
    db.plan.delete_many({})
    # --- #
    for plan_index, plan in enumerate(plans):
        date_infos = plan.select('.info_box__date')
        contents = plan.select('.info_box__text')
        for date_index, date_info in enumerate(date_infos):
            date_text = date_info.text.strip() if date_info else "날짜 정보 X"
            start_date, end_date = parse_date(date_text)
            if date_index < len(contents):
                content = contents[date_index]
                content_text = content.text.strip() if content else "내용 정보 X"
            else:
                content_text = "내용 정보 X"
            key = f"plan_{plan_index}_item_{date_index}"
            # - 중복 데이터 확인 및 방지 - #
            if not db.plan.find_one({"start_date": start_date, "end_date": end_date, "data_text": content_text}):  # - 동일 key가 존재하는지 확인 - #
                db.plan.insert_one({
                    "key": key,
                    "start_date": start_date,
                    "end_date": end_date,
                    "data_text": content_text
                })
    # --- #
    return jsonify({'result': 'success'})

@app.route('/computer', methods=['GET', 'POST'])
def get_computer():
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get('https://www.kyonggi.ac.kr/u_computer/contents.do?key=2157', headers=headers)
    data.encoding = 'utf-8'
    soup = BeautifulSoup(data.text, 'html.parser')
    study_goals = soup.select('.bu > li')
    course_goals = soup.select('p')
    db.departComputer.delete_many({})
    sg_values = [sg.text.strip() for sg in study_goals]
    cg_values = [cg.text.strip() for cg in course_goals]
    dict = {
        "sg_value": sg_values,
        "cg_value": cg_values
    }
    db.departComputer.insert_one(dict)
    return jsonify({'result': 'success'})

@app.route('/free', methods=['GET', 'POST'])
def get_free():
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get('https://www.kyonggi.ac.kr/open_major/contents.do?key=9924', headers=headers)
    data.encoding = 'utf-8'
    soup = BeautifulSoup(data.text, 'html.parser')
    study_goals = soup.select('.cts_right > .r_01')
    db.departFree.delete_many({})
    sg_values = [sg.text.strip() for sg in study_goals]
    dict = {
        "sg_value": sg_values
    }
    db.departFree.insert_one(dict)
    return jsonify({'result': 'success'})

@app.route('/showComputer', methods=['GET', 'POST'])
def read_computer():
    result = db.departComputer.find_one({}, {'_id': 0})
    return jsonify({'univ_depart': result})

@app.route('/showFree', methods=['GET', 'POST'])
def read_free():
    result = db.departFree.find_one({}, {'_id': 0})
    return jsonify({'univ_depart': result})

@app.route('/showNotice', methods=['GET', 'POST'])
def read_notice():
    result = db.notice.find_one({}, {'_id': 0})
    return jsonify({'recent_notice': result})

@app.route('/showPlan', methods=['GET', 'POST'])
def read_plan():
    result = list(db.plan.find({}, {'_id': 0}))
    return jsonify({'univ_plan': result})

if __name__ == '__main__':
    db.notice.drop()
    app.run('0.0.0.0', port=5000, debug=True)
