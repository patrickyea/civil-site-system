# 🏗️ 土木工地日常行政與材料進出貨管理系統

## 1. 系統簡介
本系統以 **Python + Streamlit + SQLite** 開發，針對土木工地與營造廠日常行政痛點，將紙本單據與零散 Excel 表單整合為關聯式資料庫網頁系統。

## 2. 本機啟動步驟
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 3. 雲端免費部署步驟（Streamlit Community Cloud）
1. 將 `app.py` 與 `requirements.txt` 上傳至 GitHub Repository。
2. 登入 [Streamlit Community Cloud](https://share.streamlit.io/)，點擊 **New app** 選擇該 Repository 與 `app.py` 即可取得公開網址。
