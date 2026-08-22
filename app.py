import streamlit as st
from database import Database
from game import GameManager
from student import StudentPage
from teacher import TeacherPage
from ui import UI


# CONFIG
st.set_page_config(
    page_title="مين أكثر؟",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# UI
UI.setup()

# DATABASE
@st.cache_resource
def get_database():
    return Database(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

db = get_database()

# GAME
game = GameManager(db)

# PAGES
teacher_page = TeacherPage(database=db, game=game)
student_page = StudentPage(database=db, game=game)

# SESSION STATE
if "student_name" not in st.session_state:
    st.session_state.student_name = None

if "show_qr" not in st.session_state:
    st.session_state.show_qr = False

if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False

# ROUTING
page = st.query_params.get("page", "display")

if page == "student":
    student_page.render()

else:
    teacher_page.render()