import io
import qrcode
import streamlit as st

class UI:
    @staticmethod
    def setup():
        st.markdown("""
        <style>

        @import url(
            'https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap'
        );

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

        .card {
            background: white;
            border-radius: 20px;
            padding: 25px;
            margin: 10px 0;
            box-shadow: 0 5px 25px rgba(0,0,0,0.07);
            border: 1px solid #eeeeee;
        }

        .question-card {
            background: linear-gradient(
                135deg,
                #fff7fb,
                #f5f7ff
            );

            border-radius: 25px;
            padding: 40px 30px;
            margin: 20px 0;
            text-align: center;

            box-shadow:
                0 8px 30px rgba(0,0,0,0.08);
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

        .success-card {
            background: #f0fff4;
            border: 1px solid #c6f6d5;
            border-radius: 18px;
            padding: 20px;
            text-align: center;
        }

        .pause-card {
            background: #fffaf0;
            border: 1px solid #f6d365;
            border-radius: 18px;
            padding: 25px;
            text-align: center;
        }

        .control-title {
            text-align: center;
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 15px;
        }

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

    # TITLE
    @staticmethod
    def title(title="مين أكثر؟", subtitle=None):
        st.markdown(f"""<div class="main-title">{title}</div>""", unsafe_allow_html=True)

        if subtitle:
            st.markdown(f"""<div class="subtitle">{subtitle}</div>""", unsafe_allow_html=True)

    # QUESTION
    @staticmethod
    def question_card(question, remaining=None, paused=False):
        if paused:
            st.markdown(
                f"""
                <div class="pause-card">
                    <h2>⏸️ اللعب متوقف مؤقتًا</h2>
                    <div class="question-text">{question}</div>
                    <div class="timer">{remaining}</div>
                    <div>ثانية متبقية</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:
            st.markdown(
                f"""
                <div class="question-card">
                    <div class="question-text">{question}</div>
                    <div class="timer">{remaining}</div>
                    <div style="color:#777;">ثانية متبقية</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # QR
    @staticmethod
    def generate_qr(url):
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)

        image = qr.make_image()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        return buffer.getvalue()

    @staticmethod
    def show_qr(url):
        qr = UI.generate_qr(url)

        st.markdown(
            """
            <div class="card">
                <h3 style="text-align:center;">امسح QR Code للدخول</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns(
            [1, 2, 1]
        )

        with col2:
            st.image(qr, width=330)

    # STAT
    @staticmethod
    def stat(number, label):
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{number}</div>
                <div class="stat-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # SUCCESS
    @staticmethod
    def success(title, message=None):
        message_html = f"{message}" if message else ""

        st.markdown(
            f"""
            <div class="success-card">
                <h3>{title}</h3>
                <p>{message_html}</p>
            </div>
            """,
            unsafe_allow_html=True
        )