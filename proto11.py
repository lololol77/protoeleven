import sqlite3
import streamlit as st
import pandas as pd

# 하드코딩된 능력치 점수 데이터 (엑셀 파일을 바탕으로 변환)
df = pd.read_excel('/mnt/data/장애유형_직무능력_매칭표 (2).xlsx')

# 장애유형과 장애정도에 맞는 능력치 딕셔너리 생성
능력치 = {}

for _, row in df.iterrows():
    for 장애유형 in df.columns[2:]:
        장애정도 = row['정도']
        능력 = row['능력']
        점수 = row[장애유형]
        
        if 장애유형 not in 능력치:
            능력치[장애유형] = {}
        if 장애정도 not in 능력치[장애유형]:
            능력치[장애유형][장애정도] = {}
        
        능력치[장애유형][장애정도][능력] = 점수

# 장애유형과 장애정도에 맞는 점수 계산
def 직무_매칭_점수_계산(일자리_제목, 필요한_능력, 장애유형, 장애정도):
    if 장애유형 not in 능력치 or 장애정도 not in 능력치[장애유형]:
        return 0  # 장애유형과 장애정도가 없으면 0점 처리

    매칭_점수 = []

    for 능력 in 필요한_능력:
        if 능력 in 능력치[장애유형][장애정도]:
            매칭_점수.append(능력치[장애유형][장애정도][능력])
        else:
            매칭_점수.append(0)  # 해당 능력이 없으면 0점으로 처리
    
    return sum(매칭_점수)

# 구직자에게 적합한 일자리 제공 함수 (기존 DB에서 매칭 점수 계산)
def 구직자에게_제공할_일자리_리스트(장애유형, 장애정도):
    conn = 연결_기존_DB()
    cursor = conn.cursor()

    # 구직자의 장애유형 + 장애정도에 맞는 매칭 결과 추출
    cursor.execute("SELECT job_title, abilities FROM job_postings")
    직무_등록 = cursor.fetchall()

    # 매칭된 일자리 리스트
    매칭_결과 = []
    
    for 직무 in 직무_등록:
        일자리_제목 = 직무[0]
        능력들 = 직무[1].split(", ")

        # 매칭 점수 계산
        총점수 = 직무_매칭_점수_계산(일자리_제목, 능력들, 장애유형, 장애정도)

        if 총점수 >= 0:  # 점수가 0 이상인 일자리 포함
            매칭_결과.append((일자리_제목, 총점수))
    
    # 점수 기준 내림차순 정렬
    매칭_결과.sort(key=lambda x: x[1], reverse=True)

    conn.close()
    
    return 매칭_결과

# DB 연결 함수 (기존 DB에서 계산에 필요한 정보 추출)
def 연결_기존_DB():
    db_path = '/mnt/data/job_matching_new_copy.db'  # 기존 DB 파일 경로
    conn = sqlite3.connect(db_path)
    return conn

# 구직자 정보를 DB에 저장하는 함수
def 구직자_정보_저장(이름, 장애유형, 장애정도):
    conn = 연결_기존_DB()  # DB 연결
    cursor = conn.cursor()
    
    # 구직자 정보 'job_seekers' 테이블에 저장
    cursor.execute("INSERT INTO job_seekers (name, disability, severity) VALUES (?, ?, ?)", (이름, 장애유형, 장애정도))
    
    conn.commit()  # 변경 사항 커밋
    conn.close()   # DB 연결 종료

# 구인자 직무 정보 저장 함수 (새로운 DB)
def 직무_정보_저장(일자리_제목, 능력들):
    conn = 연결_기존_DB()
    cursor = conn.cursor()

    # 능력들을 쉼표로 구분하여 하나의 문자열로 처리
    능력들_문자열 = ", ".join(능력들)

    # 구인자 직무 정보 저장 (일자리 제목과 능력들)
    cursor.execute("INSERT INTO job_postings (job_title, abilities) VALUES (?, ?)", 
                   (일자리_제목, 능력들_문자열))
    
    # 능력들을 abilities 테이블에 저장
    for 능력 in 능력들:
        cursor.execute("INSERT OR IGNORE INTO abilities (name) VALUES (?)", (능력,))
    
    conn.commit()
    conn.close()

# Streamlit UI 예시
st.title("장애인 일자리 매칭 시스템")

역할 = st.selectbox("사용자 역할 선택", ["구직자", "구인자"])

# 구직자 기능
if 역할 == "구직자":
    이름 = st.text_input("이름 입력")
    장애유형 = st.selectbox("장애유형", ["시각장애", "청각장애"])
    장애정도 = st.selectbox("장애 정도", ["심하지 않은", "심한"])
   
    if st.button("매칭 결과 보기"):  # 구직자 매칭 버튼
        # 구직자 정보 저장
        구직자_정보_저장(이름, 장애유형, 장애정도)
    
        st.write(f"구직자 정보가 저장되었습니다: {이름}, {장애유형}, {장애정도}")
    
        # 구인자가 등록한 직무 정보를 바탕으로 매칭 제공
        매칭_결과 = 구직자에게_제공할_일자리_리스트(장애유형, 장애정도)

        # 매칭된 일자리 목록 출력
        if len(매칭_결과) > 0:
            st.write("### 적합한 일자리 목록:")
            for 일자리_제목, 점수 in 매칭_결과:
                st.write(f"- {일자리_제목}: {점수}점")
        else:
            st.write("적합한 일자리가 없습니다.")

# 구인자 기능
elif 역할 == "구인자":
    일자리_제목 = st.text_input("일자리 제목 입력")
    능력들 = st.multiselect("필요한 능력 선택", ["주의력", "아이디어 발상 및 논리적 사고", "기억력", "지각능력", "수리능력", "공간능력", "언어능력", "지구력", "유연성 · 균형 및 조정", "체력", "움직임 통제능력", "정밀한 조작능력", "반응시간 및 속도", "청각 및 언어능력", "시각능력"])
    
    if st.button("등록"):  
        직무_정보_저장(일자리_제목, 능력들)
        st.success("구인자 정보가 저장되었습니다!")
        st.write("일자리 제목:", 일자리_제목)
        st.write("필요 능력:", ", ".join(능력들))  # 능력 리스트를 쉼표로 구분해서 표시
