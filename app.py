import io
import random
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotly.express as px
import qrcode
import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# CONFIG --------------------------------------------------------------------------------------------------------------------------------------
st.set_page_config(page_title="مين أكثر؟", age_icon="🎉", ayout="wide")
VOTING_SECONDS = 10

# SUPABASE --------------------------------------------------------------------------------------------------------------------------------------
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

supabase = get_supabase()

# SESSION STATE --------------------------------------------------------------------------------------------------------------------------------------
if "student_name" not in st.session_state:
    st.session_state.student_name = None

# DATABASE --------------------------------------------------------------------------------------------------------------------------------------
def get_students():
    response = supabase.table("students").select("*").order("name").execute()
    return response.data

def get_game_state():
    response = supabase.table("game_state").select("*").eq("id", 1).single().execute()
    return response.data

def get_questions():
    response = supabase.table("questions").select("*").order("id").execute()
    return response.data

def get_current_question(question_id):
    if question_id is None:
        return None

    response = supabase.table("questions").select("*").eq("id", question_id).single().execute()
    return response.data

def get_votes(question_id):
    response = supabase.table("votes").select("*").eq("question_id", question_id).execute()
    return response.data

# QUESTIONS --------------------------------------------------------------------------------------------------------------------------------------
def add_question(question, student):
    supabase.table("questions").insert({
        "question": question,
        "created_by": student,
        "used": False
    }).execute()

# GAME CONTROL --------------------------------------------------------------------------------------------------------------------------------------
def start_question(question_id):
    end_time = datetime.now(timezone.utc) + timedelta(seconds=VOTING_SECONDS)

    supabase.table("questions").update({"used": True}).eq("id", question_id).execute()

    supabase.table("game_state").update({
        "status": "voting",
        "current_question_id": question_id,
        "voting_ends_at": end_time.isoformat(),
        "question_type": None,
        "score_applied": False

    }).eq("id", 1).execute()

def close_voting():
    supabase.table("game_state").update({"status": "result"}).eq("id", 1).execute()

def set_question_type(question_type):
    supabase.table("game_state").update({"question_type": question_type}).eq("id", 1).execute()

# VOTING --------------------------------------------------------------------------------------------------------------------------------------
def submit_vote(question_id, voter, selected):
    try:
        supabase.table("votes").insert({
            "question_id": question_id,
            "voter_name": voter,
            "selected_name": selected
        }).execute()

        return True

    except Exception:
        return False

# SCORES --------------------------------------------------------------------------------------------------------------------------------------
def apply_scores(question_id, question_type):
    state = get_game_state()

    if state["score_applied"]:
        return

    votes = get_votes(question_id)
    counts = {}

    for vote in votes:
        name = vote["selected_name"]
        counts[name] = counts.get(name, 0) + 1

    multiplier = 1

    if question_type == "negative":
        multiplier = -1

    for name, count in counts.items():
        response = supabase.table("students").select("score").eq("name", name).single().execute()
        current_score = response.data["score"]
        new_score = current_score + count * multiplier
        supabase.table("students").update({"score": new_score}).eq("name", name).execute()

    supabase.table("game_state").update({"score_applied": True}).eq("id", 1).execute()

# QR CODE --------------------------------------------------------------------------------------------------------------------------------------
def generate_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

def get_app_url():
    return st.context.url

# DISPLAY PAGE
def display_page():
    state = get_game_state()

    if state["status"] == "waiting":
        st.markdown("""
            <h1 style="text-align:center;">مين أكثر؟</h1>
            <h2 style="text-align:center;">امسح QR Code للدخول</h2>
            """, unsafe_allow_html=True
        )

        student_url = get_app_url() + "?page=student"
        qr = generate_qr(student_url)
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.image(qr, width=350)

        students = get_students()

        st.markdown(f"""<h3 style="text-align:center;">{len(students)} طالب</h3>""", unsafe_allow_html=True)

        questions = get_questions()
        st.divider()

        st.write(f"الأسئلة المكتوبة: **{len(questions)}**")

        unused = [q for q in questions if not q["used"]]

        if len(unused) == 0:
            st.warning("لا توجد أسئلة جاهزة.")

        if st.button("ابدأ الفعالية", use_container_width=True):
            if unused:
                question = random.choice(unused)
                start_question(question["id"])
                st.rerun()

    # VOTING
    elif state["status"] == "voting":

        question = get_current_question(state["current_question_id"])
        st.markdown(f"""<h1 style="text-align:center;">{question["question"]}</h1>""", unsafe_allow_html=True)

        end_time = datetime.fromisoformat(state["voting_ends_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        remaining = int((end_time - now).total_seconds())
        remaining = max(0, remaining)

        st.markdown(f"""<h1 style="text-align:center;">{remaining}</h1>""", unsafe_allow_html=True)
        votes = get_votes(question["id"])
        students = get_students()

        vote_counts = {s["name"]: 0 for s in students}

        for vote in votes:
            name = vote["selected_name"]
            if name in vote_counts:
                vote_counts[name] += 1

        df = pd.DataFrame({
            "الاسم": list(vote_counts.keys()),
            "الأصوات": list(vote_counts.values())
        })

        fig = px.bar(df, x="الاسم", y="الأصوات", title="التصويت الحالي")
        st.plotly_chart(fig, use_container_width=True)

        if remaining <= 0:
            close_voting()
            st.rerun()

        st_autorefresh(interval=1000, key="display_timer")

    # RESULT
    elif state["status"] == "result":
        question = get_current_question(state["current_question_id"])
        st.markdown("""<h1 style="text-align:center;"> النتائج</h1>""", unsafe_allow_html=True)
        st.subheader(question["question"])
        votes = get_votes(question["id"])
        students = get_students()

        vote_counts = {s["name"]: 0 for s in students}

        for vote in votes:
            name = vote["selected_name"]
            if name in vote_counts:
                vote_counts[name] += 1

        df = pd.DataFrame({
            "الاسم": list(vote_counts.keys()),
            "الأصوات": list(vote_counts.values())
        })

        df = df.sort_values("الأصوات", ascending=False)

        fig = px.bar(df, x="الاسم", y="الأصوات", title="نتيجة التصويت")
        st.plotly_chart(fig, use_container_width=True)
        st.divider()
        st.subheader("نوع السؤال")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("إيجابي +", use_container_width=True):
                set_question_type("positive")
                apply_scores(question["id"], "positive")
                st.rerun()

        with col2:
            if st.button("سلبي -", use_container_width=True):
                set_question_type("negative")
                apply_scores(question["id"], "negative")
                st.rerun()

        state = get_game_state()

        if state["question_type"]:
            st.success("تم تحديث النقاط.")
            questions = get_questions()
            unused = [q for q in questions if not q["used"]]

            if unused:
                if st.button("السؤال التالي", use_container_width=True):
                    next_question = random.choice(unused)
                    start_question(next_question["id"])
                    st.rerun()

            else:
                if st.button("عرض النتائج النهائية", use_container_width=True):
                    supabase.table("game_state").update({"status": "finished"}).eq("id", 1).execute()
                    st.rerun()

    # FINISHED
    elif state["status"] == "finished":
        st.markdown("""<h1 style="text-align:center;">النتائج النهائية</h1>""", unsafe_allow_html=True)
        students = get_students()

        df = pd.DataFrame(students)
        df = df.sort_values("score", ascending=False)

        fig = px.bar(df, x="name", y="score", title="النقاط النهائية")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df[["name", "score"]],
            use_container_width=True,
            hide_index=True
        )

# STUDENT PAGE
def student_page():
    # LOGIN
    if st.session_state.student_name is None:
        st.title("مين أكثر؟")
        st.subheader("اختاري اسمك")
        students = get_students()
        names = [s["name"] for s in students]
        selected = st.selectbox("الاسم", ["اختاري اسمك"] + names)

        if st.button("دخول", use_container_width=True):
            if selected != "اختاري اسمك":
                st.session_state.student_name = selected
                st.rerun()

        return

    # LOGGED IN
    student = st.session_state.student_name
    state = get_game_state()
    st.title(f"مرحبًا {student}")

    # WAITING
    if state["status"] == "waiting":
        st.info("انتظري حتى تبدأ الفعالية.")
        st.subheader("اكتبي سؤالًا")

        question = st.text_area("السؤال", placeholder="مثال: مين أكثر شخص ممكن ودك تشتغل معه من جديد؟ ")
        if st.button("إرسال السؤال", use_container_width=True):
            question = question.strip()

            if question:
                add_question(question, student)
                st.success("تم إرسال سؤالك!")

            else:
                st.warning("اكتبي سؤال أولًا.")

    # VOTING
    elif state["status"] == "voting":
        question = get_current_question(state["current_question_id"])
        st.markdown(f"## {question['question']}")

        end_time = datetime.fromisoformat(state["voting_ends_at"].replace("Z", "+00:00"))
        remaining = int((end_time - datetime.now(timezone.utc)).total_seconds())
        remaining = max(0, remaining)
        st.markdown(f"### الوقت المتبقي: {remaining}")

        votes = get_votes(question["id"])
        already_voted = any(v["voter_name"] == student for v in votes)

        if already_voted:
            st.success("تم تسجيل تصويتك.")

        elif remaining <= 0:
            st.warning("انتهى وقت التصويت.")

        else:
            students = get_students()
            names = [s["name"] for s in students]

            selected = st.radio("اختاري شخصًا واحدًا", names)

            if st.button("تصويت", use_container_width=True):
                success = submit_vote(question["id"], student, selected)

                if success:
                    st.success("تم تسجيل تصويتك!")
                    st.rerun()

                else:
                    st.warning("تم تسجيل تصويتك مسبقًا.")

        st_autorefresh(interval=1000, key="student_timer")

    # RESULT
    elif state["status"] == "result":
        st.info("انتهى التصويت.")
        st.write("انتظري السؤال التالي.")
        st_autorefresh(interval=2000, key="student_result")

    # FINISHED
    elif state["status"] == "finished":
        st.success("انتهت الفعالية!")

        students = get_students()

        df = pd.DataFrame(students)

        df = df.sort_values("score", ascending=False)

        st.dataframe(
            df[["name", "score"]],
            use_container_width=True,
            hide_index=True
        )

# ROUTING
page = st.query_params.get("page", "display")

if page == "student":
    student_page()

else:
    display_page()