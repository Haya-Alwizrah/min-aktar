import random

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from results import ResultsPage
from ui import UI


class TeacherPage:

    def __init__(
        self,
        database,
        game
    ):

        self.db = database
        self.game = game

        self.results = ResultsPage(
            database
        )

    # ========================================================
    # MAIN
    # ========================================================

    def render(self):

        if "show_qr" not in st.session_state:
            st.session_state.show_qr = False

        if "confirm_reset" not in st.session_state:
            st.session_state.confirm_reset = False

        state = self.game.get_state()

        # QR
        if st.session_state.show_qr:

            self.show_qr()

            if st.button(
                "إغلاق QR",
                use_container_width=True
            ):

                st.session_state.show_qr = False

                st.rerun()

            st.divider()

        # ====================================================
        # STATE ROUTING
        # ====================================================

        if state["status"] == "waiting":

            self.waiting_screen(
                state
            )

        elif state["status"] == "voting":

            self.voting_screen(
                state
            )

        elif state["status"] == "paused":

            self.paused_screen(
                state
            )

        elif state["status"] == "result":

            self.result_screen(
                state
            )

        elif state["status"] == "finished":

            self.finished_screen(
                state
            )

    # ========================================================
    # QR
    # ========================================================

    def show_qr(self):

        student_url = (
            st.context.url
            + "?page=student"
        )

        UI.show_qr(
            student_url
        )

    # ========================================================
    # WAITING
    # ========================================================

    def waiting_screen(
        self,
        state
    ):

        UI.title(
            "مين أكثر؟",
            "استعدوا للجولة!"
        )

        if not st.session_state.show_qr:

            self.show_qr()

        st_autorefresh(
            interval=2000,
            key="teacher_waiting_refresh"
        )

        joined_count = (
            self.db.get_joined_students_count()
        )

        questions = (
            self.db.get_questions()
        )

        unused = [
            q
            for q in questions
            if not q["used"]
        ]

        # ====================================================
        # STATS
        # ====================================================

        col1, col2, col3 = st.columns(3)

        with col1:

            UI.stat(
                joined_count,
                "المشاركون"
            )

        with col2:

            UI.stat(
                len(questions),
                "الأسئلة المكتوبة"
            )

        with col3:

            UI.stat(
                len(unused),
                "الأسئلة المتبقية"
            )

        st.divider()

        if not unused:

            st.warning(
                "لا توجد أسئلة جاهزة لبدء الفعالية."
            )

        if st.button(
            "🚀 ابدأ الفعالية",
            use_container_width=True,
            type="primary"
        ):

            if unused:

                question = random.choice(
                    unused
                )

                self.game.start_question(
                    question["id"]
                )

                st.rerun()

        self.controls(
            state
        )

    # ========================================================
    # VOTING
    # ========================================================

    def voting_screen(
        self,
        state
    ):

        question = self.db.get_question(
            state["current_question_id"]
        )

        if not question:

            st.error(
                "تعذر العثور على السؤال."
            )

            return

        remaining = (
            self.game.get_remaining_seconds(
                state
            )
        )

        UI.title(
            "مين أكثر؟"
        )

        UI.question_card(
            question["question"],
            remaining
        )

        # ====================================================
        # VOTES CHART
        # ====================================================

        self.show_vote_chart(
            question["id"],
            "التصويت الحالي"
        )

        # ====================================================
        # TIME ENDED
        # ====================================================

        if remaining <= 0:

            self.game.close_voting()

            st.rerun()

        # ====================================================
        # CONTROLS
        # ====================================================

        self.controls(
            state
        )

        st_autorefresh(
            interval=1000,
            key=f"teacher_voting_{question['id']}"
        )

    # ========================================================
    # PAUSED
    # ========================================================

    def paused_screen(
        self,
        state
    ):

        question = self.db.get_question(
            state["current_question_id"]
        )

        if not question:

            st.error(
                "تعذر العثور على السؤال."
            )

            return

        remaining = (
            self.game.get_remaining_seconds(
                state
            )
        )

        UI.title(
            "مين أكثر؟"
        )

        UI.question_card(
            question["question"],
            remaining,
            paused=True
        )

        self.show_vote_chart(
            question["id"],
            "التصويت الحالي"
        )

        self.controls(
            state
        )

        st_autorefresh(
            interval=1500,
            key=f"teacher_paused_{question['id']}"
        )

    # ========================================================
    # RESULT
    # ========================================================

    def result_screen(
        self,
        state
    ):

        question = self.db.get_question(
            state["current_question_id"]
        )

        if not question:

            st.error(
                "تعذر العثور على السؤال."
            )

            return

        UI.title(
            "النتيجة 🎉"
        )

        # ====================================================
        # QUESTION
        # ====================================================

        st.markdown(
            f"""
            <div class="question-card">

                <div class="question-text">
                    {question["question"]}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        # لا يوجد اسم صاحب السؤال هنا

        st.divider()

        # ====================================================
        # CHART
        # ====================================================

        self.show_vote_chart(
            question["id"],
            "نتيجة التصويت"
        )

        st.divider()

        state = self.game.get_state()

        # ====================================================
        # QUESTION TYPE
        # ====================================================

        if not state["question_type"]:

            st.subheader(
                "هل السؤال إيجابي أم سلبي؟"
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "إيجابي +",
                    use_container_width=True,
                    type="primary"
                ):

                    self.game.set_question_type(
                        "positive"
                    )

                    self.game.apply_scores(
                        question["id"],
                        "positive"
                    )

                    st.rerun()

            with col2:

                if st.button(
                    "سلبي -",
                    use_container_width=True
                ):

                    self.game.set_question_type(
                        "negative"
                    )

                    self.game.apply_scores(
                        question["id"],
                        "negative"
                    )

                    st.rerun()

        else:

            st.success(
                "تم تحديث النقاط بنجاح."
            )

            unused = (
                self.game.get_unused_questions()
            )

            if unused:

                if st.button(
                    "السؤال التالي ➜",
                    use_container_width=True,
                    type="primary"
                ):

                    self.game.next_question()

                    st.rerun()

            else:

                if st.button(
                    "عرض النتائج النهائية",
                    use_container_width=True,
                    type="primary"
                ):

                    self.game.finish_game()

                    st.rerun()

        self.controls(
            state
        )

    # ========================================================
    # FINISHED
    # ========================================================

    def finished_screen(
        self,
        state
    ):

        self.results.render()

        self.controls(
            state
        )

    # ========================================================
    # VOTE CHART
    # ========================================================

    def show_vote_chart(
        self,
        question_id,
        title
    ):

        counts = self.db.get_vote_counts(
            question_id
        )

        if not counts:

            st.info(
                "لم يتم تسجيل أي تصويت حتى الآن."
            )

            return

        df_data = []

        for name, count in counts.items():

            if count >= 1:

                df_data.append({
                    "الاسم": name,
                    "الأصوات": count
                })

        if not df_data:

            st.info(
                "لم يتم تسجيل أي تصويت حتى الآن."
            )

            return

        import plotly.express as px

        df = (
            __import__("pandas")
            .DataFrame(df_data)
            .sort_values(
                "الأصوات",
                ascending=False
            )
        )

        fig = px.bar(
            df,
            x="الاسم",
            y="الأصوات",
            title=title,
            text="الأصوات"
        )

        fig.update_layout(
            font=dict(
                family="Cairo",
                size=15
            ),
            title_x=0.5,
            xaxis_title="",
            yaxis_title="عدد الأصوات",
            showlegend=False
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"teacher_chart_{question_id}_{title}"
        )

    # ========================================================
    # CONTROLS
    # ========================================================

    def controls(
        self,
        state
    ):

        st.divider()

        st.markdown(
            '<div class="control-title">تحكم المعلم</div>',
            unsafe_allow_html=True
        )

        status = state["status"]

        # ====================================================
        # VOTING
        # ====================================================

        if status == "voting":

            col1, col2, col3 = st.columns(3)

            with col1:

                if st.button(
                    "⏸️ إيقاف مؤقت",
                    use_container_width=True
                ):

                    self.game.pause()

                    st.rerun()

            with col2:

                if st.button(
                    "⏭️ تخطي السؤال",
                    use_container_width=True
                ):

                    self.game.skip_question()

                    st.rerun()

            with col3:

                if st.button(
                    "📱 إظهار QR",
                    use_container_width=True
                ):

                    st.session_state.show_qr = True

                    st.rerun()

        # ====================================================
        # PAUSED
        # ====================================================

        elif status == "paused":

            col1, col2, col3 = st.columns(3)

            with col1:

                if st.button(
                    "▶️ استكمال اللعب",
                    use_container_width=True,
                    type="primary"
                ):

                    self.game.resume()

                    st.rerun()

            with col2:

                if st.button(
                    "⏭️ تخطي السؤال",
                    use_container_width=True
                ):

                    self.game.skip_question()

                    st.rerun()

            with col3:

                if st.button(
                    "📱 إظهار QR",
                    use_container_width=True
                ):

                    st.session_state.show_qr = True

                    st.rerun()

        # ====================================================
        # ALL OTHER STATES
        # ====================================================

        else:

            if st.button(
                "📱 إظهار QR",
                use_container_width=True
            ):

                st.session_state.show_qr = True

                st.rerun()

        # ====================================================
        # RESET ALWAYS AVAILABLE
        # ====================================================

        st.divider()

        if st.button(
            "🔄 إعادة اللعبة من البداية",
            use_container_width=True
        ):

            st.session_state.confirm_reset = True

            st.rerun()

        # ====================================================
        # RESET CONFIRMATION
        # ====================================================

        if st.session_state.confirm_reset:

            st.warning(
                "هل أنت متأكد؟ سيتم حذف أسئلة وتصويتات "
                "الفعالية الحالية وتصفير النقاط."
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "نعم، إعادة اللعبة",
                    use_container_width=True,
                    type="primary"
                ):

                    self.game.reset_game()

                    st.session_state.confirm_reset = False
                    st.session_state.show_qr = False

                    st.rerun()

            with col2:

                if st.button(
                    "إلغاء",
                    use_container_width=True
                ):

                    st.session_state.confirm_reset = False

                    st.rerun()