import io
import random
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotly.express as px
import qrcode
import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="مين أكثر؟",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="collapsed"
)

VOTING_SECONDS = 10


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif;
}

.stApp {
    direction: rtl;
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Main title */
.main-title {
    text-align: center;
    font-size: 3.2rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
}

.subtitle {
    text-align: center;
    color: #777;
    font-size: 1.2rem;
    margin-bottom: 2rem;
}

/* Cards */
.card {
    background: white;
    border-radius: 20px;
    padding: 25px;
    margin: 10px 0;
    box-shadow: 0 5px 25px rgba(0,0,0,0.07);
    border: 1px solid #eeeeee;
}

.question-card {
    background: linear-gradient(135deg, #fff7fb, #f5f7ff);
    border-radius: 25px;
    padding: 40px 30px;
    margin: 20px 0;
    text-align: center;
    box-shadow: 0 8px 30px rgba(0,0,0,0.08);
}

.question-text {
    font-size: 2.3rem;
    font-weight: 800;
    line-height: 1.7;
}

.timer {
    text-align: center;
    font-size: 4rem;
    font-weight: 800;
    margin: 10px 0;
}

.waiting-text {
    text-align: center;
    font-size: 1.5rem;
    color: #777;
    margin: 30px 0;
}

/* Stats */
.stat-card {
    background: white;
    border-radius: 18px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.stat-number {
    font-size: 2.2rem;
    font-weight: 800;
}

.stat-label {
    color: #777;
    font-size: 1rem;
}

/* Success */
.success-card {
    background: #f0fff4;
    border: 1px solid #c6f6d5;
    border-radius: 18px;
    padding: 20px;
    text-align: center;
}

/* Hide Streamlit decoration */
#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SUPABASE
# ============================================================

@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


supabase = get_supabase()


# ============================================================
# SESSION STATE
# ============================================================

if "student_name" not in st.session_state:
    st.session_state.student_name = None


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_students():

    response = (
        supabase
        .table("students")
        .select("*")
        .order("name")
        .execute()
    )

    return response.data or []


def get_game_state():

    response = (
        supabase
        .table("game_state")
        .select("*")
        .eq("id", 1)
        .single()
        .execute()
    )

    return response.data


def get_questions():

    response = (
        supabase
        .table("questions")
        .select("*")
        .order("id")
        .execute()
    )

    return response.data or []


def get_current_question(question_id):

    if question_id is None:
        return None

    response = (
        supabase
        .table("questions")
        .select("*")
        .eq("id", question_id)
        .single()
        .execute()
    )

    return response.data


def get_votes(question_id):

    response = (
        supabase
        .table("votes")
        .select("*")
        .eq("question_id", question_id)
        .execute()
    )

    return response.data or []


# ============================================================
# STUDENT HISTORY
# ============================================================

def get_student_question(student):

    response = (
        supabase
        .table("questions")
        .select("*")
        .eq("created_by", student)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def has_voted(question_id, student):

    response = (
        supabase
        .table("votes")
        .select("id")
        .eq("question_id", question_id)
        .eq("voter_name", student)
        .limit(1)
        .execute()
    )

    return bool(response.data)


# ============================================================
# JOINED STUDENTS
# ============================================================

def mark_student_joined(student):

    try:

        supabase.table("students").update({
            "joined_at": datetime.now(
                timezone.utc
            ).isoformat()
        }).eq(
            "name",
            student
        ).execute()

        return True

    except Exception:

        return False


def get_joined_students_count():

    try:

        response = (
            supabase
            .table("students")
            .select("name")
            .not_.is_("joined_at", "null")
            .execute()
        )

        return len(response.data or [])

    except Exception:

        return 0


# ============================================================
# QUESTIONS
# ============================================================

def add_question(question, student):

    # الطالب لا يستطيع إرسال أكثر من سؤال
    existing = get_student_question(student)

    if existing:
        return False

    try:

        supabase.table("questions").insert({
            "question": question,
            "created_by": student,
            "used": False
        }).execute()

        return True

    except Exception:

        return False


# ============================================================
# GAME CONTROL
# ============================================================

def start_question(question_id):

    end_time = (
        datetime.now(timezone.utc)
        + timedelta(seconds=VOTING_SECONDS)
    )

    supabase.table("questions").update({
        "used": True
    }).eq(
        "id",
        question_id
    ).execute()

    supabase.table("game_state").update({
        "status": "voting",
        "current_question_id": question_id,
        "voting_ends_at": end_time.isoformat(),
        "question_type": None,
        "score_applied": False
    }).eq(
        "id",
        1
    ).execute()


def close_voting():

    supabase.table("game_state").update({
        "status": "result"
    }).eq(
        "id",
        1
    ).execute()


def set_question_type(question_type):

    supabase.table("game_state").update({
        "question_type": question_type
    }).eq(
        "id",
        1
    ).execute()


# ============================================================
# RESET GAME
# ============================================================

def reset_game():

    """
    إعادة اللعبة بالكامل من الصفر.

    يتم:
    1. حذف التصويتات
    2. حذف الأسئلة
    3. تصفير النقاط
    4. تصفير joined_at
    5. إعادة game_state إلى waiting
    6. تسجيل خروج الطالب من الجلسة الحالية
    """

    # حذف التصويتات القديمة
    supabase.table("votes") \
        .delete() \
        .neq("id", 0) \
        .execute()

    # حذف الأسئلة القديمة
    supabase.table("questions") \
        .delete() \
        .neq("id", 0) \
        .execute()

    # تصفير الطلاب
    try:

        supabase.table("students").update({
            "score": 0,
            "joined_at": None
        }).neq(
            "id",
            0
        ).execute()

    except Exception:

        # إذا joined_at غير موجود
        supabase.table("students").update({
            "score": 0
        }).neq(
            "id",
            0
        ).execute()

    # إعادة حالة اللعبة
    supabase.table("game_state").update({

        "status": "waiting",

        "current_question_id": None,

        "voting_ends_at": None,

        "question_type": None,

        "score_applied": False

    }).eq(
        "id",
        1
    ).execute()

    # تسجيل خروج الطالب الحالي
    st.session_state.student_name = None


# ============================================================
# VOTING
# ============================================================

def submit_vote(question_id, voter, selected):

    # حماية إضافية
    if has_voted(question_id, voter):
        return False

    try:

        supabase.table("votes").insert({

            "question_id": question_id,

            "voter_name": voter,

            "selected_name": selected

        }).execute()

        return True

    except Exception:

        return False


# ============================================================
# SCORES
# ============================================================

def apply_scores(question_id, question_type):

    state = get_game_state()

    if state["score_applied"]:
        return

    votes = get_votes(question_id)

    counts = {}

    for vote in votes:

        name = vote["selected_name"]

        counts[name] = (
            counts.get(name, 0) + 1
        )

    multiplier = 1

    if question_type == "negative":
        multiplier = -1

    for name, count in counts.items():

        response = (
            supabase
            .table("students")
            .select("score")
            .eq("name", name)
            .single()
            .execute()
        )

        if response.data:

            current_score = response.data["score"]

            new_score = (
                current_score
                + count * multiplier
            )

            supabase.table("students").update({

                "score": new_score

            }).eq(
                "name",
                name
            ).execute()

    supabase.table("game_state").update({

        "score_applied": True

    }).eq(
        "id",
        1
    ).execute()


# ============================================================
# VOTE COUNTS
# ============================================================

def get_vote_counts(question_id):

    votes = get_votes(question_id)

    counts = {}

    for vote in votes:

        name = vote["selected_name"]

        counts[name] = (
            counts.get(name, 0) + 1
        )

    return counts


def create_vote_chart(question_id, title):

    counts = get_vote_counts(question_id)

    # لا يوجد تصويت
    if not counts:

        st.info(
            "لم يتم تسجيل أي تصويت حتى الآن."
        )

        return

    # فقط من حصلوا على صوت واحد أو أكثر
    counts = {
        name: count
        for name, count in counts.items()
        if count >= 1
    }

    if not counts:

        st.info(
            "لم يتم تسجيل أي تصويت حتى الآن."
        )

        return

    df = pd.DataFrame({

        "الاسم": list(counts.keys()),

        "الأصوات": list(counts.values())

    })

    df = df.sort_values(
        "الأصوات",
        ascending=False
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

        key=f"chart_{question_id}_{title}"

    )


# ============================================================
# QR CODE
# ============================================================

def generate_qr(url):

    qr = qrcode.QRCode(

        version=1,

        box_size=10,

        border=4

    )

    qr.add_data(url)

    qr.make(fit=True)

    image = qr.make_image()

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG"
    )

    return buffer.getvalue()


def get_app_url():

    return st.context.url


# ============================================================
# QUESTION OWNER
# ============================================================

def show_question_owner(question):

    key = f"owner_{question['id']}"

    if st.button(

        "👤 معرفة صاحب السؤال",

        key=key,

        use_container_width=True

    ):

        st.info(
            f"كاتب السؤال: **{question['created_by']}**"
        )


# ============================================================
# DISPLAY PAGE
# ============================================================

def display_page():

    state = get_game_state()


    # ========================================================
    # WAITING
    # ========================================================

    if state["status"] == "waiting":

        st.markdown(
            '<div class="main-title">مين أكثر؟</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="subtitle">استعدوا للجولة!</div>',
            unsafe_allow_html=True
        )

        student_url = (
            get_app_url()
            + "?page=student"
        )

        qr = generate_qr(student_url)

        col1, col2, col3 = st.columns(
            [1, 2, 1]
        )

        with col2:

            st.markdown(
                '<div class="card">',
                unsafe_allow_html=True
            )

            st.markdown(
                """
                <h3 style='text-align:center;'>
                    امسح QR Code للدخول
                </h3>
                """,
                unsafe_allow_html=True
            )

            st.image(
                qr,
                width=330
            )

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )


        # تحديث عدد المشاركين والأسئلة
        st_autorefresh(
            interval=2000,
            key="display_waiting_refresh"
        )


        joined_count = (
            get_joined_students_count()
        )

        questions = get_questions()

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
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{joined_count}</div>
                    <div class="stat-label">المشاركون</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div class="stat-card">
                    <div class="stat-number">{len(questions)}</div>
                    <div class="stat-label">الأسئلة المكتوبة</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f"""
                <div class="stat-card">
                    <div class="stat-number">{len(unused)}</div>
                    <div class="stat-label">الأسئلة المتبقية</div>
                </div>
                """,
                unsafe_allow_html=True
            )


        st.divider()

        if not unused:
            st.warning("لا توجد أسئلة جاهزة لبدء الفعالية.")

        if st.button(
            "🚀 ابدأ الفعالية",
            use_container_width=True,
            type="primary"

        ):
            if unused:
                question = random.choice(unused)
                start_question(question["id"])
                st.rerun()


    # ========================================================
    # VOTING
    # ========================================================

    elif state["status"] == "voting":

        question = get_current_question(
            state["current_question_id"]
        )

        if not question:

            st.error("تعذر العثور على السؤال.")

            return


        end_time = datetime.fromisoformat(

            state["voting_ends_at"].replace(
                "Z",
                "+00:00"
            )

        )

        remaining = int(

            (
                end_time
                - datetime.now(timezone.utc)
            ).total_seconds()

        )

        remaining = max(
            0,
            remaining
        )


        st.markdown(
            '<div class="main-title">مين أكثر؟</div>',
            unsafe_allow_html=True
        )


        st.markdown(

            f"""
            <div class="question-card">

                <div class="question-text">
                    {question["question"]}
                </div>

                <div class="timer">
                    {remaining}
                </div>

                <div style="color:#777;">
                    ثانية متبقية
                </div>

            </div>
            """,

            unsafe_allow_html=True

        )


        # الرسم يتحدث مع كل refresh
        create_vote_chart(

            question["id"],

            "التصويت الحالي"

        )


        # إغلاق تلقائي
        if remaining <= 0:

            close_voting()

            st.rerun()


        st_autorefresh(

            interval=1000,

            key=f"display_voting_{question['id']}"

        )


    # ========================================================
    # RESULT
    # ========================================================

    elif state["status"] == "result":

        question = get_current_question(
            state["current_question_id"]
        )

        if not question:

            st.error(
                "تعذر العثور على السؤال."
            )

            return


        st.markdown(
            '<div class="main-title">النتيجة 🎉</div>',
            unsafe_allow_html=True
        )


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


        # معرفة صاحب هذا السؤال فقط
        show_question_owner(question)


        st.divider()


        # نتيجة التصويت
        create_vote_chart(

            question["id"],

            "نتيجة التصويت"

        )


        st.divider()


        state = get_game_state()


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

                    set_question_type(
                        "positive"
                    )

                    apply_scores(

                        question["id"],

                        "positive"

                    )

                    st.rerun()


            with col2:

                if st.button(

                    "سلبي -",

                    use_container_width=True

                ):

                    set_question_type(
                        "negative"
                    )

                    apply_scores(

                        question["id"],

                        "negative"

                    )

                    st.rerun()


        else:

            st.success(
                "تم تحديث النقاط بنجاح."
            )


            questions = get_questions()

            unused = [

                q

                for q in questions

                if not q["used"]

            ]


            if unused:

                if st.button(

                    "السؤال التالي ➜",

                    use_container_width=True,

                    type="primary"

                ):

                    next_question = random.choice(
                        unused
                    )

                    start_question(
                        next_question["id"]
                    )

                    st.rerun()


            else:

                if st.button(

                    "عرض النتائج النهائية",

                    use_container_width=True,

                    type="primary"

                ):

                    supabase.table(
                        "game_state"
                    ).update({

                        "status": "finished"

                    }).eq(
                        "id",
                        1
                    ).execute()

                    st.rerun()


    # ========================================================
    # FINISHED
    # ========================================================

    elif state["status"] == "finished":

        st.markdown(
            '<div class="main-title">النتائج النهائية 🏆</div>',
            unsafe_allow_html=True
        )


        students = get_students()

        df = pd.DataFrame(students)


        if df.empty:

            st.info(
                "لا توجد نتائج."
            )

            return


        df = df.sort_values(

            "score",

            ascending=False

        )


        fig = px.bar(

            df,

            x="name",

            y="score",

            title="النقاط النهائية",

            text="score"

        )


        fig.update_layout(

            font=dict(

                family="Cairo",

                size=15

            ),

            title_x=0.5,

            xaxis_title="",

            yaxis_title="النقاط",

            showlegend=False

        )


        fig.update_traces(
            textposition="outside"
        )


        st.plotly_chart(

            fig,

            use_container_width=True

        )


        st.dataframe(

            df[["name", "score"]],

            use_container_width=True,

            hide_index=True

        )


        # ====================================================
        # RESET GAME
        # ====================================================

        st.divider()

        st.subheader(
            "بدء فعالية جديدة"
        )

        st.write(
            "سيتم حذف أسئلة وتصويتات الفعالية الحالية "
            "وتصفير النقاط."
        )


        if st.button(

            "🔄 إعادة اللعبة",

            use_container_width=True,

            type="primary"

        ):

            reset_game()

            st.rerun()


# ============================================================
# STUDENT PAGE
# ============================================================

def student_page():


    # ========================================================
    # LOGIN
    # ========================================================

    if st.session_state.student_name is None:

        st.markdown(
            '<div class="main-title">مين أكثر؟</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="subtitle">اختاري اسمك للانضمام</div>',
            unsafe_allow_html=True
        )


        students = get_students()

        names = [
            s["name"]
            for s in students
        ]


        selected = st.selectbox(

            "الاسم",

            names,

            index=None,

            placeholder="اختاري اسمك..."

        )


        if st.button(

            "دخول",

            use_container_width=True,

            type="primary"

        ):

            if selected:

                st.session_state.student_name = selected

                # حفظ دخول الطالب
                mark_student_joined(
                    selected
                )

                st.rerun()

            else:

                st.warning(
                    "اختاري اسمك أولًا."
                )


        return


    # ========================================================
    # LOGGED IN
    # ========================================================

    student = st.session_state.student_name

    state = get_game_state()


    st.markdown(
        f"""
        <div class="main-title">
            مرحبًا {student}
        </div>
        """,

        unsafe_allow_html=True

    )


    # ========================================================
    # WAITING
    # ========================================================

    if state["status"] == "waiting":

        st_autorefresh(

            interval=2000,

            key="student_waiting_refresh"

        )


        previous_question = get_student_question(
            student
        )


        if previous_question:

            st.markdown(
                """
                <div class="success-card">
                    <h3>✓ تم إرسال سؤالك</h3>
                    <p>لا يمكنك إرسال سؤال آخر.</p>
                    <p>انتظري حتى تبدأ الجولة.</p>
                </div>
                """,
                unsafe_allow_html=True
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

        else:
            st.info("اكتبي سؤالًا واحدًا فقط للعبة.")

            question = st.text_area(
                "السؤال",

                placeholder=(
                    "مثال: مين أكثر شخص ممكن "
                    "ودك تشتغل معه من جديد؟"
                ),

                height=120

            )


            if st.button(

                "إرسال السؤال",

                use_container_width=True,

                type="primary"

            ):

                question = question.strip()


                if not question:

                    st.warning(
                        "اكتبي السؤال أولًا."
                    )


                else:

                    success = add_question(

                        question,

                        student

                    )


                    if success:

                        st.success(
                            "تم إرسال سؤالك بنجاح!"
                        )

                        st.rerun()


                    else:

                        st.warning(
                            "سبق لك إرسال سؤال."
                        )


    # ========================================================
    # VOTING
    # ========================================================

    elif state["status"] == "voting":

        question = get_current_question(

            state["current_question_id"]

        )


        if not question:

            st.error(
                "تعذر العثور على السؤال."
            )

            return


        end_time = datetime.fromisoformat(

            state["voting_ends_at"].replace(
                "Z",
                "+00:00"
            )

        )


        remaining = int(

            (

                end_time
                - datetime.now(timezone.utc)

            ).total_seconds()

        )


        remaining = max(

            0,

            remaining

        )


        st.markdown(
            f"""
            <div class="question-card">
                <div class="question-text" style="font-size:1.8rem;">{question["question"]}</div>
                <div class="timer" style="font-size:3rem;">{remaining}</div>
                <div>ثانية متبقية</div>
            </div>
            """,
            unsafe_allow_html=True
        )


        already_voted = has_voted(

            question["id"],

            student

        )


        if already_voted:

            st.markdown(
                """
                <div class="success-card">
                    <h3>✓ تم تسجيل تصويتك</h3>
                    <p>انتظري ظهور النتيجة.</p>
                </div>
                """,
                unsafe_allow_html=True

            )


        elif remaining <= 0:

            st.warning(
                "انتهى وقت التصويت."
            )


        else:

            students = get_students()

            names = [
                s["name"]
                for s in students
            ]


            # قائمة منسدلة بدل عرض جميع الأسماء
            selected = st.selectbox(

                "اختاري اللاعب",

                names,

                index=None,

                placeholder=(
                    "اختاري اسم اللاعب..."
                )

            )


            if st.button(

                "تصويت",

                use_container_width=True,

                type="primary"

            ):

                if not selected:

                    st.warning(
                        "اختاري لاعبًا أولًا."
                    )

                else:

                    success = submit_vote(

                        question["id"],

                        student,

                        selected

                    )


                    if success:

                        st.success(
                            "تم تسجيل تصويتك!"
                        )

                        st.rerun()


                    else:

                        st.warning(
                            "سبق لك التصويت في هذا السؤال."
                        )


        st_autorefresh(

            interval=1000,

            key=f"student_voting_{question['id']}"

        )


    # ========================================================
    # RESULT
    # ========================================================

    elif state["status"] == "result":

        st.markdown(
            """
            <div class="success-card">
                <h3>انتهى التصويت ✓</h3>
                <p>انتظري السؤال التالي.</p>
            </div>
            """,
            unsafe_allow_html=True

        )


        st_autorefresh(

            interval=2000,

            key="student_result_refresh"

        )


    # ========================================================
    # FINISHED
    # ========================================================

    elif state["status"] == "finished":

        st.success(
            "انتهت الفعالية! 🏆"
        )


        students = get_students()

        df = pd.DataFrame(students)


        if not df.empty:

            df = df.sort_values(

                "score",

                ascending=False

            )


            st.dataframe(

                df[["name", "score"]],

                use_container_width=True,

                hide_index=True

            )


# ============================================================
# ROUTING
# ============================================================

page = st.query_params.get(
    "page",
    "display"
)


if page == "student":

    student_page()

else:

    display_page()