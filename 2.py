import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="서울 대중교통 데이터 분석")

# --- 2. [필수] 파일 경로 설정 ---
BASE_PATH = "/Users/kil07201/Desktop/py"

# --- 3. 데이터 로드 함수 ---

# [수정] 캐시 데코레이터 추가: 이 함수의 결과를 메모리에 저장합니다.
@st.cache_data
def load_congestion_data(file_name):
    """
    (CSV 로드) 혼잡도 CSV를 읽고, 'melt' 처리
    """
    data = None
    full_path = os.path.join(BASE_PATH, file_name)
    try:
        data = pd.read_csv(full_path, encoding='utf-8')
    except UnicodeDecodeError:
        data = pd.read_csv(full_path, encoding='cp949') 
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {full_path}")
        return None
    except Exception as e:
        st.error(f"로드 오류: {e}")
        return None

    try:
        if not data['호선'].astype(str).str.contains('호선').all():
             data['호선'] = data['호선'].astype(str) + '호선'
    except KeyError:
        st.error("혼잡도 데이터에 '호선' 열이 없습니다.")
        return None

    try:
        id_vars = data.columns[:5]  
        time_vars = data.columns[5:] 
        data_long = pd.melt(data, id_vars=id_vars, value_vars=time_vars, 
                            var_name='시간', value_name='혼잡도')
        data_long['혼잡도'] = pd.to_numeric(data_long['혼잡도'], errors='coerce')
        data_long['시간'] = pd.Categorical(data_long['시간'], categories=time_vars, ordered=True)
        return data_long
    except Exception as e:
        st.error(f"혼잡도 데이터 변환(melt) 중 오류: {e}")
        return None

# [수정] 캐시 데코레이터 추가
@st.cache_data
def load_passenger_data(file_name):
    """
    (CSV 로드) 승하차 인원 CSV를 읽고, '요일별 평균'까지 계산
    """
    data = None
    full_path = os.path.join(BASE_PATH, file_name) 
    try:
        data = pd.read_csv(full_path, encoding='utf-8')
    except UnicodeDecodeError:
        data = pd.read_csv(full_path, encoding='cp949')
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {full_path}")
        return None
    except Exception as e:
        st.error(f"로드 오류: {e}")
        return None

    try:
        data['수송일자'] = pd.to_datetime(data['수송일자'])
        weekday_map = {0: '평일', 1: '평일', 2: '평일', 3: '평일', 4: '평일', 5: '토요일', 6: '일요일'}
        data['요일구분'] = data['수송일자'].dt.weekday.map(weekday_map)
         
        data.rename(columns={'역명': '출발역'}, inplace=True) 
        if not data['호선'].astype(str).str.contains('호선').all():
             data['호선'] = data['호선'].astype(str) + '호선'

        group_by_cols = ['요일구분', '호선', '출발역', '승하차구분']
        time_cols = data.columns[6:-1] 
        id_vars = group_by_cols
        data_long = pd.melt(data, 
                            id_vars=id_vars, 
                            value_vars=time_cols, 
                            var_name='시간대', 
                            value_name='인원수')
         
        data_long['인원수'] = pd.to_numeric(data_long['인원수'], errors='coerce')

        grouped_data = data_long.groupby(
            ['요일구분', '호선', '출발역', '승하차구분', '시간대']
        )['인원수'].mean().reset_index()
         
        grouped_data['시간대'] = pd.Categorical(grouped_data['시간대'], categories=time_cols, ordered=True)
        grouped_data = grouped_data.sort_values('시간대')
         
        return grouped_data
     
    except Exception as e:
        st.error(f"승하차 인원 데이터 처리 중 오류: {e}")
        return None

# [수정] 캐시 데코레이터 추가
@st.cache_data
def load_ranking_data(file_name):
    """
    (CSV 로드) 수송순위 CSV를 읽는 함수 (단순 로드)
    """
    data = None
    full_path = os.path.join(BASE_PATH, file_name) 
    try:
        data = pd.read_csv(full_path, encoding='utf-8')
    except UnicodeDecodeError:
        data = pd.read_csv(full_path, encoding='cp949')
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {full_path}")
        return None
    except Exception as e:
        st.error(f"로드 오류: {e}")
        return None
         
    try:
        if '호선' in data.columns:
            if not data['호선'].astype(str).str.contains('호선').all():
                 data['호선'] = data['호선'].astype(str) + '호선'
        return data
    except Exception as e:
        st.error(f"수송 순위 데이터 '호선' 처리 중 오류: {e}")
        return data

# [수정] 캐시 데코레이터 추가
@st.cache_data
def load_bus_data(location_file, status_file):
    """
    버스 위치(Excel), 현황(Excel 탭) 2개 파일을 읽고 합칩니다.
    """
    data_location = None
    data_status = None
     
    # 1. 위치 파일 로드 (Excel)
    full_path_loc = os.path.join(BASE_PATH, location_file) 
    try:
        data_location = pd.read_excel(full_path_loc, engine='openpyxl', sheet_name='Data')
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {full_path_loc}")
        return None
    except Exception as e:
        st.error(f"버스 위치(Excel) 로드 오류: {e}")
        st.warning("팁: openpyxl 라이브러리가 설치되어 있어야 합니다. (pip install openpyxl)")
        return None

    # 2. 현황 파일 로드 (Excel의 특정 탭)
    full_path_stat = os.path.join(BASE_PATH, status_file)
    try:
        sheet_name_to_load = '2023년 12월 4일 기준'
        data_status = pd.read_excel(full_path_stat, engine='openpyxl', sheet_name=sheet_name_to_load)
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {full_path_stat}")
        return None
    except Exception as e:
        st.error(f"버스 현황(Excel) 로드 오류: {e}")
        st.warning(f"팁: '{status_file}' 파일 안에 '{sheet_name_to_load}' 탭이 정확히 있는지 확인하세요.")
        return None
         
    # 3. '정류소명'을 기준으로 두 데이터 합치기 (merge)
    try:
        if '정류소명' not in data_location.columns or 'NODE_ID' not in data_location.columns:
            st.error(f"{location_file}의 'Data' 탭에 '정류소명' 또는 'NODE_ID' 열이 없습니다.")
            return None
        if '정류소명' not in data_status.columns or '노선수' not in data_status.columns:
            st.error(f"{status_file}의 '{sheet_name_to_load}' 탭에 '정류소명' 또는 '노선수' 열이 없습니다.")
            return None

        location_cols = ['정류소명', 'NODE_ID']
        status_cols = ['정류소명', '노선수']
         
        merged_bus_data = pd.merge(
            data_location[location_cols], 
            data_status[status_cols], 
            on='정류소명', 
            how='inner'
        )
         
        merged_bus_data = merged_bus_data.drop_duplicates('NODE_ID')
        merged_bus_data.rename(columns={'NODE_ID': '정류소번호'}, inplace=True)
         
        return merged_bus_data
         
    except Exception as e:
        st.error(f"버스 데이터 병합 중 오류: {e}")
        return None


# --- 4. 페이지 화면 함수 ---

def show_home(count, total_files):
    """홈 화면"""
    st.header("🚇 서울 대중교통 데이터 분석")
    st.text("사이드바 메뉴에서 분석 내용을 선택하세요.")
    st.image("https://mediahub.seoul.go.kr/uploads/mediahub/2024/09/jXjYOLlbMGtMRfhWswMBpgzNqagnuOrd.jpg")
    st.success(f"총 {total_files}개의 데이터 중 {count}개를 성공적으로 로드했습니다.")


def show_congestion_analysis(data_congestion, data_passenger):
    """혼잡도 분석 페이지"""
    st.header("📈 지하철 혼잡도(%) 분석")

    # [수정] set 연산을 사용해 공통 항목 계산을 더 빠르게 합니다.
    days_in_congestion = set(data_congestion['요일구분'].unique())
    days_in_passenger = set(data_passenger['요일구분'].unique())
    common_days = sorted(list(days_in_congestion & days_in_passenger))

    if not common_days:
        st.error("분석할 공통 요일 데이터가 없습니다.")
        return

    lines_in_congestion = set(data_congestion['호선'].unique())
    lines_in_passenger = set(data_passenger['호선'].unique())
    common_lines = sorted(list(lines_in_congestion & lines_in_passenger))
    
    if not common_lines:
        st.error("분석할 공통 호선 데이터가 없습니다.")
        return

    col1, col2 = st.columns(2)
    with col1:
        selected_day = st.selectbox("요일 선택", common_days, key="cong_day")
    with col2:
        selected_line = st.selectbox("호선 선택", common_lines, key="cong_line")
     
    directions = sorted(data_congestion[
        (data_congestion['요일구분']==selected_day) &
        (data_congestion['호선']==selected_line)
    ]['상하구분'].unique())
    selected_dir = st.selectbox("방향 선택", directions, key="cong_dir")

    stations_in_congestion = set(data_congestion[
        (data_congestion['요일구분']==selected_day) &
        (data_congestion['호선']==selected_line)
    ]['출발역'].unique())
    
    stations_in_passenger = set(data_passenger[
        (data_passenger['요일구분']==selected_day) &
        (data_passenger['호선']==selected_line)
    ]['출발역'].unique())
    
    common_stations = sorted(list(stations_in_congestion & stations_in_passenger))
     
    if not common_stations:
        st.warning("선택한 조건에 맞는 공통 역 데이터가 없습니다.")
        return

    selected_stations = st.multiselect("역 선택 (다중 선택 가능)", common_stations, default=common_stations[0], key="cong_station")
    if not selected_stations:
        st.warning("역을 1개 이상 선택하세요.")
        return

    filtered = data_congestion[
        (data_congestion['요일구분']==selected_day) &
        (data_congestion['호선']==selected_line) &
        (data_congestion['상하구분']==selected_dir) &
        (data_congestion['출발역'].isin(selected_stations))
    ].copy()
    filtered['혼잡도'] = filtered['혼잡도'].fillna(0) 

    if filtered.empty:
        st.warning("선택한 조건의 혼잡도 데이터가 없습니다.")
        return

    fig = px.line(filtered, x='시간', y='혼잡도', color='출발역', markers=True,
                  title=f"{selected_day} / {selected_line} / {selected_dir} 시간대별 혼잡도")
    fig.update_layout(xaxis_title="시간", yaxis_title="혼잡도 (%)", xaxis={'type': 'category'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(filtered)


def show_passenger_analysis(data_congestion, data_passenger):
    """승하차 인원 분석 페이지"""
    st.header("👥 지하철 승하차 인원(명) 분석")
     
    # [수정] set 연산을 사용해 공통 항목 계산을 더 빠르게 합니다.
    days_in_congestion = set(data_congestion['요일구분'].unique())
    days_in_passenger = set(data_passenger['요일구분'].unique())
    common_days = sorted(list(days_in_congestion & days_in_passenger))

    if not common_days:
        st.error("분석할 공통 요일 데이터가 없습니다.")
        return

    lines_in_congestion = set(data_congestion['호선'].unique())
    lines_in_passenger = set(data_passenger['호선'].unique())
    common_lines = sorted(list(lines_in_congestion & lines_in_passenger))
    
    if not common_lines:
        st.error("분석할 공통 호선 데이터가 없습니다.")
        return

    col1, col2 = st.columns(2)
    with col1:
        selected_day = st.selectbox("요일 선택", common_days, key="pass_day")
    with col2:
        selected_line = st.selectbox("호선 선택", common_lines, key="pass_line")
     
    ride_types = sorted(data_passenger['승하차구분'].unique())
    selected_ride = st.radio("승하차 구분", ride_types, horizontal=True, key="pass_type")
     
    stations_in_congestion = set(data_congestion[
        (data_congestion['요일구분']==selected_day) &
        (data_congestion['호선']==selected_line)
    ]['출발역'].unique())
    
    stations_in_passenger = set(data_passenger[
        (data_passenger['요일구분']==selected_day) &
        (data_passenger['호선']==selected_line)
    ]['출발역'].unique())
    
    common_stations = sorted(list(stations_in_congestion & stations_in_passenger))
     
    if not common_stations:
        st.warning("선택한 조건에 맞는 공통 역 데이터가 없습니다.")
        return

    selected_stations = st.multiselect("역 선택 (다중 선택 가능)", common_stations, default=common_stations[0], key="pass_station")
    if not selected_stations:
        st.warning("역을 1개 이상 선택하세요.")
        return

    filtered = data_passenger[
        (data_passenger['요일구분']==selected_day) &
        (data_passenger['호선']==selected_line) &
        (data_passenger['출발역'].isin(selected_stations)) &
        (data_passenger['승하차구분']==selected_ride)
    ].copy()
    filtered['인원수'] = filtered['인원수'].fillna(0).round(0).astype(int)

    if filtered.empty:
        st.warning("선택한 조건의 승하차 데이터가 없습니다.")
        return

    fig = px.bar(filtered, x='시간대', y='인원수', color='출발역', barmode='group',
             title=f"{selected_day} / {selected_line} 시간대별 {selected_ride} 인원 (일평균)")
    fig.update_layout(xaxis_title="시간대", yaxis_title="평균 인원수 (명)", xaxis={'type': 'category'})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(filtered)


def show_ranking(data_ranking):
    """수송 순위 페이지"""
    st.header("🏆 지하철 수송 순위 (2024년 기준)")
     
    if '호선' in data_ranking.columns:
        all_lines = list(data_ranking['호선'].unique())
        all_lines.insert(0, "전체 호선") 
        selected_line = st.selectbox("조회할 호선 선택", all_lines, key="rank_line")
        if selected_line == "전체 호선":
            filtered_data = data_ranking
        else:
            filtered_data = data_ranking[data_ranking['호선'] == selected_line]
        st.dataframe(filtered_data.reset_index(drop=True))
    else:
        st.dataframe(data_ranking)


# --- ⬇️⬇️⬇️ [수정된 함수] ⬇️⬇️⬇️ ---

# [수정] 무거운 환승 허브 계산을 별도 함수로 분리하고 캐시 적용
@st.cache_data
def calculate_transfer_hubs(data_passenger, data_bus):
    """
    Top 10 지하철역의 연계 버스 노선 수를 계산하는 (무거운) 함수
    """
    # 1. '평일' '승차' 기준 일평균 승객 Top 10 지하철역 추출
    passenger_filtered = data_passenger[
        (data_passenger['요일구분'] == '평일') &
        (data_passenger['승하차구분'] == '승차')
    ]
    passenger_sum = passenger_filtered.groupby('출발역')['인원수'].sum().reset_index()
    top_10_stations = passenger_sum.sort_values(by='인원수', ascending=False).head(10)
    top_10_stations['인원수'] = top_10_stations['인원수'].round(0).astype(int)
     
    # 2. Top 10 역을 순회하며 연계 버스 노선 수 계산
    bus_route_counts = [] # 버스 노선 수를 저장할 빈 리스트
     
    for station_name in top_10_stations['출발역']:
        # '강남'역의 경우, '강남역', '강남역.12번출구' 등을 모두 찾아야 함
        relevant_stops = data_bus[data_bus['정류소명'].str.contains(station_name, na=False)]
         
        # 찾은 정류소들의 '노선수'를 모두 합산
        total_routes = relevant_stops['노선수'].sum()
        bus_route_counts.append(total_routes)
         
    # 3. Top 10 지하철역 데이터에 '연계 버스 노선 수' 열 추가
    top_10_stations['연계 버스 노선 수'] = bus_route_counts
    top_10_stations['연계 버스 노선 수'] = top_10_stations['연계 버스 노선 수'].astype(int)
    
    return top_10_stations


def show_summary_analysis(data_congestion, data_passenger, data_ranking, data_bus):
    """
    [수정] 4개 데이터를 모두 사용한 종합 분석 대시보드
    """
    st.header("📊 종합 분석 대시보드")
    st.info("지하철 역 기준으로 주변 정류장의 버스 노선을 집계하여 가능한 노선 수를 나타냅니다.")

    # --- 1. 기존 지하철 Top 5 분석 ---
    st.subheader("🚇 지하철 핵심 현황 Top 5")
    col1, col2 = st.columns(2)
     
    with col1:
        try:
            st.markdown("#### 🏆 2024년 수송 순위")
            # [수정] 이 계산은 매우 빠르므로 캐시가 불필요합니다.
            top_5_ranking = data_ranking.sort_values('순위').head(5)
            st.dataframe(top_5_ranking)
        except Exception as e:
            st.error(f"수송 순위 Top 5 분석 중 오류: {e}")
            st.dataframe(data_ranking.head(5))

    with col2:
        try:
            st.markdown("#### 🥵 2025년 최고 혼잡도")
            # [수정] 이 계산은 매우 빠르므로 캐시가 불필요합니다.
            top_5_congestion = data_congestion.sort_values('혼잡도', ascending=False).head(5)
            st.dataframe(top_5_congestion[['호선', '출발역', '상하구분', '시간', '혼잡도']])
        except Exception as e:
            st.error(f"최고 혼잡도 Top 5 분석 중 오류: {e}")
             
    # --- 2. [신규] 환승 허브 분석 ---
    st.subheader("🚌 🆚 🚇 지하철-버스 환승 허브 분석 (Top 10)")
     
    try:
        # [수정] 캐시된 함수를 호출하여 계산을 다시 실행하지 않고 결과만 가져옵니다.
        top_10_hubs = calculate_transfer_hubs(data_passenger, data_bus)

        # 4. 결과 출력
        st.dataframe(top_10_hubs)
        st.info(" '연계 버스 노선 수'는 해당 지하철역 이름이 포함된 주변 버스정류소의 총 노선 합계입니다.")

    except Exception as e:
        st.error(f"환승 허브 분석 중 오류: {e}")
# --- ⬆️⬆️⬆️ [수정된 함수] ⬆️⬆️⬆️ ---


def show_bus_analysis(data_bus):
    """
    버스 정류소 데이터를 분석하는 페이지
    """
    st.header("🚌 버스 정류소 분석 (2023년 기준)")
    st.info("서울시 버스 정류소별 노선 수 현황입니다.")
     
    try:
        # [수정] 이 계산은 매우 빠르므로 캐시가 불필요합니다.
        top_bus_stops = data_bus.sort_values(by='노선수', ascending=False)
         
        st.subheader("📊 노선 수 기준 Top 20 버스 정류소")
        st.dataframe(top_bus_stops[['정류소명', '노선수', '정류소번호']].head(20))

        st.subheader("🔍 정류소 이름으로 검색")
        search_name = st.text_input("검색할 정류소 이름을 입력하세요 (예: 강남역)")
         
        if search_name: 
            search_result = top_bus_stops[top_bus_stops['정류소명'].str.contains(search_name)]
            if search_result.empty:
                st.warning("검색 결과가 없습니다.")
            else:
                st.dataframe(search_result)
                 
    except Exception as e:
        st.error(f"버스 데이터 분석 중 오류: {e}")
        st.warning(" '노선수', '정류소명', '정류소번호' 열이 있는지 확인하세요.")


# --- 5. 메인 프로그램 실행 ---

# 1. 파일 이름 정의
file_congestion = "서울교통공사_지하철혼잡도정보_20250630.csv"
file_passenger = "서울교통공사_역별 일별 시간대별 승하차인원 정보_20231231.csv"
file_ranking = "서울교통공사_수송순위_20241231.csv"
file_bus_location = "서울시버스정류소위치정보(20251103).xlsx" 
file_bus_status = "서울시 정류소현황(2019~2023년).xlsx" 

# 2. 데이터 로드 (이제 이 함수들은 캐시된 결과를 반환하므로 매우 빠릅니다)
data_congestion = load_congestion_data(file_congestion)
data_passenger = load_passenger_data(file_passenger)
data_ranking = load_ranking_data(file_ranking)
data_bus = load_bus_data(file_bus_location, file_bus_status)

# 3. 로드된 데이터 개수 확인
data_list = [data_congestion, data_passenger, data_ranking, data_bus]
total_files = len(data_list) 

data_loaded_count = 0
for d in data_list:
    if d is not None and not d.empty:
        data_loaded_count = data_loaded_count + 1 

# 4. 사이드바 메뉴
menu_options = [
    'HOME', 
    '📊 종합 분석 (환승 허브)',
    '🚌 버스 정류소 분석',
    '🏆 수송 순위 (지하철)',
    '📈 혼잡도 분석 (지하철)',
    '👥 승하차 분석 (지하철)'
]
menu = st.sidebar.selectbox("메뉴 선택", menu_options)

# 5. 메뉴에 따라 다른 페이지 보여주기
if menu == 'HOME':
    show_home(data_loaded_count, total_files)

elif menu == '📊 종합 분석 (환승 허브)':
    if all(d is not None and not d.empty for d in data_list):
        show_summary_analysis(data_congestion, data_passenger, data_ranking, data_bus)
    else:
        st.error("종합 분석에 필요한 4개 데이터가 모두 로드되지 않았습니다.")

elif menu == '🚌 버스 정류소 분석':
    if data_bus is not None and not data_bus.empty:
        show_bus_analysis(data_bus)
    else:
        st.error("버스 정류소 데이터를 로드하지 못했습니다.")
         
elif menu == '🏆 수송 순위 (지하철)':
    if data_ranking is not None and not data_ranking.empty:
        show_ranking(data_ranking)
    else:
        st.error("수송 순위 데이터를 로드하지 못했습니다.")

elif menu == '📈 혼잡도 분석 (지하철)':
    if data_congestion is not None and not data_congestion.empty and \
       data_passenger is not None and not data_passenger.empty:
        show_congestion_analysis(data_congestion, data_passenger)
    else:
        st.error("혼잡도 또는 승하차 데이터를 로드하지 못해 분석할 수 없습니다.")

elif menu == '👥 승하차 분석 (지하철)':
    if data_congestion is not None and not data_congestion.empty and \
       data_passenger is not None and not data_passenger.empty:
        show_passenger_analysis(data_congestion, data_passenger)
    else:
        st.error("혼잡도 또는 승하차 데이터를 로드하지 못해 분석할 수 없습니다.")