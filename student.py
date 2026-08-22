import streamlit as st
from streamlit_autorefresh import st_autorefresh
from ui import UI

class StudentPage:
    def __init__(self, database, game):
        self.db = database
        self.game = game

    # MAIN
    def render(self):
        if "student_name" not in st.session_state:
            st.session_state.student_name = None

        if st.session_state.student_name is None:
            self.login()
            return

        student = st.session_state.student_name
        state = self.game.get_state()
        UI.title(f"مرحبًا {student}")

        # ROUTING
        if state["status"] == "waiting":
            self.waiting_screen(student)

        elif state["status"] == "voting":
            self.voting_screen(student, state)

        elif state["status"] == "paused":
            self.paused_screen(state)

        elif state["status"] == "result":
            self.result_screen()

        elif state["status"] == "finished":
            self.finished_screen()

    # LOGIN
    def login(self):
        UI.title("مين أكثر؟", "اختار اسمك للانضمام")
        students = self.db.get_students()
        names = [student["name"] for student in students]

        selected = st.selectbox("الاسم", names, index=None, placeholder="اختار اسمك...")
        if st.button("دخول", use_container_width=True, type="primary"):
            if not selected:
                st.warning("اختار اسمك أولًا.")
                return

            st.session_state.student_name = selected
            self.db.mark_student_joined(selected)
            st.rerun()

    # WAITING
    def waiting_screen(self, student):
        st_autorefresh(interval=2000, key="student_waiting_refresh")
        previous_question = self.db.get_student_question(student)

        if previous_question:
            UI.success(
                "✓ تم إرسال سؤالك",
                "لا يمكنك إرسال سؤال آخر. انتظر حتى تبدأ الجولة."
            )

            st.markdown(
                f"""
                <div class="question-card">
                    <strong>سؤالك:</strong>
                    <br><br>
                    {previous_question["question"]}
                </div>
                """,
                unsafe_allow_html=True
            )
            return

        st.info("اكتب سؤالًا واحدًا فقط للعبة.")

        question = st.text_area(
            "السؤال",
            placeholder=(
                "مثال: مين أكثر شخص ممكن "
                "ودك تشتغل معه من جديد؟"
            ),
            height=120
        )

        if st.button("إرسال السؤال", use_container_width=True, type="primary"):
            question = question.strip()

            if not question:
                st.warning("اكتب السؤال أولًا.")
                return

            success = self.db.add_question(question, student)

            if success:
                st.success("تم إرسال سؤالك بنجاح!")
                st.rerun()

            else:
                st.warning("سبق لك إرسال سؤال.")

    # VOTING
    def voting_screen(self, student, state):
        question = self.db.get_question(state["current_question_id"])

        if not question:
            st.error("تعذر العثور على السؤال.")
            return

        remaining = self.game.get_remaining_seconds(state)

        # السؤال + الوقت
        UI.question_card(question["question"], remaining)

        # CHECK VOTE
        already_voted = self.db.has_voted(question["id"], student)

        if already_voted:
            UI.success(
                "✓ تم تسجيل تصويتك",
                "انتظر ظهور النتيجة."
            )

        elif remaining <= 0:
            st.warning("انتهى وقت التصويت.")

        else:
            students = self.db.get_students()
            names = [s["name"] for s in students]
            selected = st.selectbox("اختار اللاعب", names, index=None, placeholder="اختار اسم اللاعب...")

            if st.button("تصويت", use_container_width=True, type="primary"):
                if not selected:
                    st.warning("اختار لاعبًا أولًا.")
                    return

                success = self.db.submit_vote(question["id"], student, selected)

                if success:
                    st.success("تم تسجيل تصويتك!")
                    st.rerun()

                else:
                    st.warning("سبق لك التصويت في هذا السؤال.")

        # AUTO REFRESH
        st_autorefresh(interval=1000, key=f"student_voting_{question['id']}")

    # PAUSED
    def paused_screen(self, state):
        question = self.db.get_question(state["current_question_id"])

        if not question:
            st.error("تعذر العثور على السؤال.")
            return

        remaining = self.game.get_remaining_seconds(state)

        UI.question_card(question["question"], remaining, paused=True)
        st.info("انتظر حتى يستأنف اللعب.")
        st_autorefresh(interval=1000, key=f"student_paused_{question['id']}")

    # RESULT
    def result_screen(self):
        UI.success(
            "انتهى التصويت ✓",
            "انتظر السؤال التالي."
        )

        st_autorefresh(interval=1500, key="student_result_refresh")

    # FINISHED
    def finished_screen(self):
        st.success("انتهت الفعالية! 🏆")
        st.info("شكرًا لمشاركتك!")
        st_autorefresh(interval=3000, key="student_finished_refresh")