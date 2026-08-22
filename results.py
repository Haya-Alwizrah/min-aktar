import pandas as pd
import plotly.express as px
import streamlit as st

class ResultsPage:
    def __init__(self, database):
        self.db = database

    # FINAL RESULTS
    def render(self):
        st.markdown('<div class="main-title">النتائج النهائية 🏆</div>', unsafe_allow_html=True)
        students = self.db.get_students()

        if not students:
            st.info("لا توجد نتائج.")
            return

        df = pd.DataFrame(students)

        if "score" not in df.columns:
            st.info("لا توجد نتائج.")
            return

        # حذف أصحاب الصفر
        df["score"] = df["score"].fillna(0).astype(int)
        df = df[df["score"] != 0]

        if df.empty:
            st.info("لا توجد نقاط مسجلة.")
            return

        # SORT
        df = df.sort_values("score", ascending=False)

        # CHART
        fig = px.bar(
            df,
            x="name",
            y="score",
            title="النقاط النهائية",
            text="score"
        )

        fig.update_layout(
            font=dict(family="Cairo", size=15),
            title_x=0.5,
            xaxis_title="",
            yaxis_title="النقاط",
            showlegend=False
        )

        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)