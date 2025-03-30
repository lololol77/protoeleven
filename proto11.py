import sqlite3
import streamlit as st
import pandas as pd

# 하드코딩된 능력치 점수 데이터 (엑셀 파일을 바탕으로 변환)
df = pd.read_excel('장애유형_직무능력_매칭표 (2).xlsx')

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

# 직무와 능력에 대한 매칭 점수를 계산하는 함수
def 직무_매칭_점수_계산(일자리_제목, 필요한_능력, 장애유형, 장애정도):
    conn = 연결_기존_DB()
    cursor = conn.cursor()
    
    # 구직자의 장애유형 + 장애정도에 맞는 disability_type_id 확인
    def get_disability_type_id(장애유형, 장애정도):
        conn = 연결_기존_DB()
        cursor = conn.cursor()
        
        # 장애유형 + 장애정도 결합
        disability_type = f"{장애유형} {장애정도}"  # 장애유형과 장애정도를 합침
        print(f"검색할 disability_type: {disability_type}")  # 디버깅용 출력

        # disability_types 테이블에서 해당 disability_type을 찾아 disability_type_id를 반환
        cursor.execute("SELECT id FROM disability_types WHERE disability_type=?", (disability_type,))
        disability_type_id = cursor.fetchone()
        
        conn.close()
        
        if disability_type_id is None:
            print(f"장애유형 '{장애유형}'과 장애정도 '{장애정도}'에 해당하는 disability_type_id가 없습니다.")  # 디버깅 메시지
            return None  # 해당 장애유형 + 장애정도가 없으면 None 반환
        return disability_type_id[0]

    disability_type_id = get_disability_type_id(장애유형, 장애정도)
    if disability_type_id is None:
        print(f"장애유형 '{장애유형}'과 장애정도 '{장애정도}'에 해당하는 disability_type_id가 없습니다.")
        return 0

    # 매칭 점수 계산
    매칭_점수 = []
    능력_count = 0  # 유효한 능력의 수를 셈

    for 능력 in 필요한_능력:
        if 능력 is None or 능력 == "": continue  # 능력 값이 유효하지 않으면 넘어감
        
        # 능력 이름으로 매칭 처리 (abilities 테이블에서 id 조회)
        cursor.execute("SELECT id FROM abilities WHERE TRIM(UPPER(name)) = TRIM(UPPER(?))", (능력,))
        능력_id = cursor.fetchone()
        
        if 능력_id is None:
            print(f"능력 '{능력}'에 해당하는 ability_id가 없습니다.")  # 디버깅 메시지
            continue  # 능력 ID가 없다면 넘어감
        
        # 장애유형과 장애정도에 맞는 능력 점수 가져오기 (matching 테이블에서)
        cursor.execute("""
            SELECT suitability 
            FROM matching 
            WHERE disability_type_id=? AND ability_id=? 
        """, (disability_type_id, 능력_id[0]))
        
        적합도 = cursor.fetchone()
        
        if 적합도 is None:
            적합도 = (0,)  # 적합도가 없다면 0으로 처리
        
        적합도 = 적합도[0]
        매칭_점수.append(적합도)
        능력_count += 1  # 유효한 능력 개수 증가
    
    # 점수 합계 계산 (유효한 능력만)
    if 능력_count == 0:
        return 0  # 유효한 능력이 없으면 점수 0
    
    총점수 = sum(매칭_점수)
    conn.close()
    
    return 총점


# 구직자에게 적합한 일자리 제공 함수 (기존 DB에서 매칭 점수 계산)
def 구직자에게_제공할_일자리_리스트(장애유형, 장애정도):
    conn = 연결_새로운_DB()
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

# DB 연결 함수 (새로운 DB에서 계산에 필요한 정보 추출)
def 연결_새로운_DB():
    db_path = '/mnt/data/job_postings.db'  # 구인자 직무 정보 저장 DB 경로
    conn = sqlite3.connect(db_path)
    return conn

# 구직자 정보를 DB에 저장하는 함수
def 구직자_정보_저장(이름, 장애유형, 장애정도):
    conn = 연결_기존_DB()  # 기존 DB 연결
    cursor = conn.cursor()
    
    # 구직자 정보 'job_seekers' 테이블에 저장
    cursor.execute("INSERT INTO job_seekers (name, disability, severity) VALUES (?, ?, ?)", (이름, 장애유형, 장애정도))
    
    conn.commit()  # 변경 사항 커밋
    conn.close()   # DB 연결 종료

# 구인자 직무 정보 저장 함수 (새로운 DB)
def 직무_정보_저장(일자리_제목, 능력들, 유료서비스):
    conn = 연결_새로운_DB()
    cursor = conn.cursor()

    # 능력들을 쉼표로 구분하여 하나의 문자열로 처리
    능력들_문자열 = ", ".join(능력들)

    # 구인자 직무 정보 저장 (일자리 제목과 능력들, 유료 서비스 정보)
    cursor.execute("INSERT INTO job_postings (job_title, abilities, paid_service) VALUES (?, ?, ?)", 
                   (일자리_제목, 능력들_문자열, 유료서비스))
    
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
    장애유형 = st.selectbox("장애유형", ["시각장애", "청각장애", "지체장애", "뇌병변장애", "언어장애", "안면장애", "신장장애", "심장장애", "간장애", "호흡기장애", "장루·요루장애", "뇌전증장애", "지적장애", "자폐성장애", "정신장애"])
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
    
    # 유료 서비스 질문
    유료_서비스 = st.radio("유료 직무개발 서비스 이용하시겠습니까?", ["네", "아니요"])
    
    if st.button("등록"):  
        직무_정보_저장(일자리_제목, 능력들, 유료_서비스)
        st.success("구인자 정보가 저장되었습니다!")
        st.write("일자리 제목:", 일자리_제목)
        st.write("필요 능력:", ", ".join(능력들))  # 능력 리스트를 쉼표로 구분해서 표시
        st.write("유료 직무개발 서비스 이용 여부:", 유료_서비스)


