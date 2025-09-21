# -*- coding: utf-8 -*-
import streamlit as st
import folium
import pandas as pd
import numpy as np
import plotly.express as px
import ee
import geemap.foliumap as geemap
import json
import os
from google.oauth2 import service_account

# -------------------- 페이지 설정 --------------------
st.set_page_config(
    page_title="물러서는 땅, 다가오는 바다 — 해수면 상승 대시보드",
    layout="wide",
    page_icon="🌊"
)

# -------------------- GEE 인증 --------------------
@st.cache_resource
def initialize_ee():
    try:
        creds_dict = None
        if hasattr(st, 'secrets') and st.secrets.get("gcp_service_account"):
            creds_dict = st.secrets["gcp_service_account"]
        else:
            secret_value = os.environ.get('GEE_JSON_KEY')
            if secret_value:
                creds_dict = json.loads(secret_value)
        if not creds_dict:
            st.error("🚨 GEE 인증 정보를 찾을 수 없습니다. GitHub 또는 Streamlit Secret 설정을 확인하세요.")
            st.stop()
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        scoped_credentials = credentials.with_scopes([
            'https://www.googleapis.com/auth/earthengine',
            'https://www.googleapis.com/auth/cloud-platform'
        ])
        ee.Initialize(credentials=scoped_credentials)
        st.sidebar.success("✅ GEE 인증 성공!")
        return True
    except Exception as e:
        st.error(f"🚨 GEE 인증 오류가 발생했습니다.\n\n오류 상세: {e}")
        st.stop()

# -------------------------
# Helper / 투발루 그래프용 데이터
# -------------------------
@st.cache_data
def generate_tuvalu_graph_data():
    rng = np.random.RandomState(42)
    rows = []
    years = list(range(1990, 2051))
    base, trend = 0.03, 0.004
    for year in years:
        years_from0 = year - min(years)
        sea = float(np.round(base + trend * years_from0 + rng.normal(scale=0.002), 3))
        rows.append({"country": "투발루", "year": year, "sea_level_mm": max(0.0, sea * 1000)})
    return pd.DataFrame(rows)

df_tuvalu_graph = generate_tuvalu_graph_data()

# -------------------------
# 사이드바: 사용자 입력
# -------------------------
st.sidebar.title("🔧 설정")
st.sidebar.markdown("연도를 선택하면 지도가 실시간으로 갱신됩니다.")
sel_year = st.sidebar.slider("연도 선택", min_value=2025, max_value=2100, value=2050, step=5)
show_tuvalu = st.sidebar.checkbox("투발루 상세 보기", value=True)

# -------------------------
# 메인 화면 구성
# -------------------------
st.title("🌊 물러서는 땅, 다가오는 바다: 해수면 상승 대시보드")

# --- 지도 ---
st.header(f"🗺️ {sel_year}년 예상 해수면 상승 위험 지도")
initialize_ee()

DEM = ee.Image('NASA/NASADEM_HGT/001').select('elevation')
POPULATION = ee.ImageCollection('WorldPop/GP/100m/pop').filterDate('2020').mean()

# 해수면 상승 가정 (점점 더 심각하게)
sea_level_rise = (sel_year - 2025) / 75 * 1.5  # 단위: m

with st.spinner("🌍 지도 데이터를 불러오는 중..."):
    flooded_mask_global = DEM.lte(sea_level_rise).selfMask()
    affected_population_heatmap = POPULATION.updateMask(flooded_mask_global)
    
    heatmap_vis_params = {
        'min': 0, 
        'max': 300,
        'palette': ['#ffeda0','#feb24c','#f03b20','#bd0026']  # 연한 노랑 → 주황 → 빨강
    }
    
    m = geemap.Map(center=[0, 0], zoom=2)
    m.add_basemap('SATELLITE')
    
    map_id_dict = affected_population_heatmap.getMapId(heatmap_vis_params)
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        overlay=True,
        name=f'{sel_year}년 인구 피해 히트맵',
        show=True
    ).add_to(m)
    
    folium.LayerControl().add_to(m)

m.to_streamlit(height=850)

st.markdown("---")

# --- 보고서 ---
st.header("📘 해수면 상승의 위험과 우리의 대처법")
st.subheader("🔹 서론 — 문제 제기")
st.markdown(
    "산업혁명 이후 대기 중 **이산화탄소 농도는 40% 이상 증가**했고, 그 결과 지구 평균 기온은 약 1.1℃ 상승했습니다. "
    "이 작은 변화가 빙하를 녹이고, 바닷물을 팽창시켜 해수면 상승을 가속화하고 있습니다.  \n\n"
    "특히 **해발 5m 이하의 저지대**에 거주하는 약 **6억 명** 인구는 삶의 터전을 잃을 위험에 놓여 있습니다."
)

st.subheader("🔹 본론 1 — 데이터 분석")
st.markdown(
    "이 대시보드는 NASA의 지형 데이터(NASADEM)와 WorldPop의 인구 분포 데이터를 활용합니다.  \n"
    "- 지도는 연도별 예상 침수 지역과 인구 분포를 겹쳐 시각화했습니다.  \n"
    "- **색이 진할수록 피해 인구가 많음을 의미**합니다.  \n"
    "- 21세기 후반으로 갈수록 피해 범위가 급격히 확대되는 경향이 나타납니다."
)

st.subheader("🔹 본론 2 — 원인 및 영향 사례")
st.markdown("**📍 투발루 (Tuvalu)**")
st.markdown(
    "- 평균 해발고도 2~3m의 작은 섬나라로, 이미 농지 침수와 식수원 오염이 심각합니다.  \n"
    "- 국제 사회에 '환경 난민 수용'을 요청했지만 받아들여지지 않고 있습니다.  \n"
    "- 지도에서 사라질 수 있다는 이유로 '**21세기의 아틀란티스**'라 불립니다."
)

st.markdown("**📍 몰디브 (Maldives)**")
st.markdown(
    "- 평균 해발고도 1.5m, 관광산업 의존도가 높은 국가.  \n"
    "- 해수면 상승으로 리조트와 해안선이 침식되며 국가 경제가 위협받고 있습니다."
)

st.markdown("**📍 방글라데시 (Bangladesh)**")
st.markdown(
    "- 갠지스 삼각주 지역은 해수면 상승에 극도로 취약합니다.  \n"
    "- 매년 수백만 명이 홍수 피해를 입으며, 농지 염분화로 식량 위기도 심화됩니다."
)

st.subheader("🔹 본론 3 — 청소년이 알아야 할 핵심 포인트")
st.markdown(
    "1. 해수면 상승은 단순한 환경문제가 아니라 **사회·경제·문화적 위기**입니다.  \n"
    "2. 피해는 전 세계적으로 불균등하게 분포하며, 가난한 나라일수록 더 큰 타격을 입습니다.  \n"
    "3. 기후 변화 대응은 **완화(Mitigation)**와 **적응(Adaptation)**이 동시에 필요합니다."
)

st.subheader("🔹 결론 — 우리의 대응")
st.markdown(
    "- **국가적 대응**: 방파제 건설, 연안 개발 제한, 국제적 협력 강화.  \n"
    "- **기술적 대응**: 재생에너지 확대, 친환경 도시 설계.  \n"
    "- **개인적 대응**: 에너지 절약, 생활 속 탄소발자국 줄이기.  \n"
)

st.markdown("---")

# --- 투발루 그래프 (애니메이션 추가) ---
if show_tuvalu:
    st.header("📈 투발루 해수면 상승 추이 (1990~2050)")
    fig_tuv = px.scatter(
        df_tuvalu_graph,
        x="year", y="sea_level_mm",
        animation_frame="year", animation_group="country",
        range_y=[0, 300],
        labels={"sea_level_mm": "해수면 상승 (mm)", "year": "연도"},
        title="투발루 해수면 상승 (시뮬레이션)"
    )
    fig_tuv.update_traces(mode="lines+markers", line=dict(color="blue", width=3))
    st.plotly_chart(fig_tuv, use_container_width=True)
    st.info("💡 투발루는 이미 국토 침수로 인해 국가 존속이 위협받고 있으며, 국제 사회에 도움을 요청하고 있습니다.")

# --- 청소년 체크리스트 ---
st.header("✅ 청소년 친환경 실천 체크리스트")
options = [
    "🌱 불필요한 전등 끄기", "🚲 대중교통·자전거 이용", "🥤 일회용품 줄이기",
    "🍽️ 음식물 쓰레기 줄이기", "♻️ 철저한 분리배출", "🛍️ 친환경 제품 사용",
    "🌍 환경 동아리 참여", "🏖️ 해안/하천 정화 활동", "🌳 나무 심기", "📢 기후 캠페인 참여"
]
checked = []
cols = st.columns(2)
for i, opt in enumerate(options):
    with cols[i % 2]:
        if st.checkbox(opt, key=f"act_{i}"):
            checked.append(opt)

if checked:
    st.success(f"👏 {len(checked)}개의 항목을 실천하기로 약속했어요!")
    df_checked = pd.DataFrame({"실천 항목": checked})
    st.download_button(
        "📥 나의 다짐 다운로드",
        data=df_checked.to_csv(index=False).encode("utf-8"),
        file_name="my_climate_actions.csv",
        mime="text/csv"
    )

# --- 맺음말 ---
st.markdown("---")
st.subheader("🌏 마무리 — 지금 우리가 해야 할 일")
st.markdown(
    "해수면 상승은 미래의 이야기가 아니라 이미 현재 진행 중인 위기입니다. "
    "이 대시보드가 경각심을 주고, 작은 행동이 큰 변화를 만들어낼 수 있다는 확신을 주길 바랍니다."
)
