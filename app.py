import streamlit as st
import psycopg2
import hashlib

st.set_page_config(
    page_title="ClassLevel LMS Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN UI & CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stCard {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    h1, h2, h3 { color: #1e293b; font-family: 'Inter', sans-serif; }
    .stButton>button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
    </style>
""", unsafe_allow_html=True)


def get_db_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text


# Cədvəllərin Yeni Tələblərə Uyğun Genişləndirilməsi
try:
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL,
        username VARCHAR(50) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role VARCHAR(20) NOT NULL,
        student_code VARCHAR(10) UNIQUE,
        class_level INT DEFAULT 5,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id SERIAL PRIMARY KEY,
        title VARCHAR(150) NOT NULL,
        class_level INT NOT NULL,
        content TEXT,
        main_standard VARCHAR(255),
        sub_standard VARCHAR(255),
        file_url TEXT,
        video_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Quiz paketləri cədvəli (Quiz adı, çətinlik, vaxt)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_packages (
        id SERIAL PRIMARY KEY,
        class_level INT NOT NULL,
        title VARCHAR(150) NOT NULL,
        difficulty VARCHAR(50) DEFAULT 'Orta',
        duration_minutes INT DEFAULT 10,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Suallar cədvəli (Quiz paketlərinə bağlı)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id SERIAL PRIMARY KEY,
        package_id INT REFERENCES quiz_packages(id) ON DELETE CASCADE,
        question_text TEXT NOT NULL,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_option VARCHAR(1)
    );
    """)

    # Şagird statistikaları üçün cədvəl
    cur.execute("""
    CREATE TABLE IF NOT EXISTS student_stats (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50),
        videos_watched INT DEFAULT 0,
        total_watch_minutes INT DEFAULT 0,
        quizzes_taken INT DEFAULT 0,
        total_correct INT DEFAULT 0,
        total_questions_answered INT DEFAULT 0
    );
    """)

    admin_user = "admin"
    admin_pass = make_hashes("Muellim2026")
    cur.execute("SELECT id FROM users WHERE username = %s", (admin_user,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (full_name, username, password, role, student_code, class_level)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ("Müəllim (Admin)", admin_user, admin_pass, "admin", "000", 0))

    conn.commit()
    cur.close()
    conn.close()
except Exception as e:
    st.error(f"❌ Verilənlər Bazası Xətası: {e}")

# Session State Tənzimləmələri
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "user_role" not in st.session_state:
    st.session_state["user_role"] = ""
if "full_name" not in st.session_state:
    st.session_state["full_name"] = ""
if "class_level" not in st.session_state:
    st.session_state["class_level"] = 5
if "student_page" not in st.session_state:
    st.session_state["student_page"] = "Əsas səhifə"

# --- GİRİŞ / QEYDİYYAT SƏHİFƏSİ ---
if not st.session_state["logged_in"]:
    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    with col_c2:
        st.markdown("<h1 style='text-align: center; color: #4f46e5;'>🎓 ClassLevel LMS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>Müasir Təhsil və İdarəetmə Portalı</p>",
                    unsafe_allow_html=True)
        st.write("")

        tab_login, tab_reg = st.tabs(["🔑 Sistemə Giriş", "📝 Yeni Qeydiyyat"])

        with tab_login:
            u_input = st.text_input("İstifadəçi adı:", key="l_user")
            p_input = st.text_input("Şifrə:", type="password", key="l_pass")
            st.write("")
            if st.button("Daxil Ol", use_container_width=True):
                if u_input and p_input:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT full_name, username, password, role, class_level FROM users WHERE username = %s",
                            (u_input.strip(),))
                        udata = cur.fetchone()
                        cur.close()
                        conn.close()
                        if udata and check_hashes(p_input, udata[2]):
                            st.session_state["logged_in"] = True
                            st.session_state["username"] = udata[1]
                            st.session_state["full_name"] = udata[0]
                            st.session_state["user_role"] = udata[3]
                            st.session_state["class_level"] = int(udata[4]) if udata[4] else 5
                            st.rerun()
                        else:
                            st.error("Yanlış istifadəçi adı və ya şifrə!")
                    except Exception as ex:
                        st.error(f"Xəta: {ex}")

        with tab_reg:
            r_fn = st.text_input("Ad və Soyad:")
            r_un = st.text_input("İstifadəçi Adı (Username):")
            r_pw = st.text_input("Şifrə:", type="password")
            r_cl = st.selectbox("Sinif:", list(range(1, 12)), index=8)
            r_cd = st.text_input("Müəllimin verdiyi 3 rəqəmli Şagird Kodu:", max_chars=3)
            st.write("")
            if st.button("Qeydiyyatı Tamamla", use_container_width=True):
                if r_fn and r_un and r_pw and r_cd:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        hashed_pw = make_hashes(r_pw)
                        cur.execute(
                            "INSERT INTO users (full_name, username, password, role, student_code, class_level) VALUES (%s, %s, %s, %s, %s, %s)",
                            (r_fn.strip(), r_un.strip(), hashed_pw, 'student', r_cd.strip(), int(r_cl)))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Qeydiyyat tamamlandı! İndi daxil ola bilərsiniz.")
                    except Exception as ex:
                        st.error(f"Qeydiyyat xətası: {ex}")
else:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['full_name']}")
        role_txt = "👨‍🏫 Müəllim (Admin)" if st.session_state[
                                                'user_role'] == 'admin' else f"🎓 {st.session_state['class_level']}-ci Sinif Şagirdi"
        st.info(role_txt)
        st.write("---")

        if st.session_state['user_role'] == 'student':
            if st.button("🏠 Əsas Səhifə / Score Board", use_container_width=True):
                st.session_state["student_page"] = "Əsas səhifə"
                st.rerun()
            if st.button("📚 Dərs Materialları", use_container_width=True):
                st.session_state["student_page"] = "Materiallar"
                st.rerun()
            if st.button("✍️ Quizlər və İmtahanlar", use_container_width=True):
                st.session_state["student_page"] = "Quizlər"
                st.rerun()
            st.write("---")

        if st.button("🚪 Çıxış Et", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- MÜƏLLİM PANELİ ---
    if st.session_state["user_role"] == "admin":
        st.markdown("<h1>👨‍🏫 Müəllim İdarəetmə Paneli</h1>", unsafe_allow_html=True)
        m_t1, m_t2, m_t3 = st.tabs(["📊 Şagirdlər", "➕ Dərs Əlavə Et", "📝 Quiz Paketi Yarat"])

        with m_t1:
            st.subheader("Qeydiyyatdakı Şagirdlər")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, full_name, username, student_code, class_level FROM users WHERE role = 'student'")
                studs = cur.fetchall()
                cur.close()
                conn.close()
                if studs:
                    st.dataframe(
                        [{"ID": s[0], "Ad Soyad": s[1], "Username": s[2], "Kod": s[3], "Sinif": f"{s[4]}-ci sinif"} for
                         s in studs], use_container_width=True)
                else:
                    st.info("Şagird yoxdur.")
            except Exception as e:
                st.error(e)

        with m_t2:
            st.subheader("Yeni Dərs Əlavə Et")
            with st.form("les_form"):
                ltitle = st.text_input("Dərs Başlığı:")
                lclass = st.selectbox("Sinif:", list(range(1, 12)), index=8)
                lcont = st.text_area("Mətn / İzah:")
                lf_url = st.text_input("PDF Fayl Linki:")
                lv_url = st.text_input("YouTube Video Linki:")
                if st.form_submit_button("Dərsi Əlavə Et"):
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO lessons (title, class_level, content, file_url, video_url) VALUES (%s, %s, %s, %s, %s)",
                            (ltitle, lclass, lcont, lf_url, lv_url))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Dərs əlavə olundu!")
                    except Exception as e:
                        st.error(e)

        with m_t3:
            st.subheader("Quiz Paketi və Sualları Tərtib Et")
            with st.form("q_pack_form"):
                q_class = st.selectbox("Hansı Sinif Üçün?", list(range(1, 12)), index=8, key="qp_cl")
                q_title = st.text_input("Quiz Adı (Məsələn: Quiz 1 - Riyaziyyat Giriş):")
                q_diff = st.selectbox("Çətinlik Səviyyəsi:", ["Asan", "Orta", "Çətin"])
                q_dur = st.number_input("Vaxt (dəqiqə ilə):", min_value=1, value=10)

                st.markdown("--- **Suallar:**")
                q_text = st.text_area("Sual Mətni:")
                opt_a = st.text_input("Variant A:")
                opt_b = st.text_input("Variant B:")
                opt_c = st.text_input("Variant C:")
                opt_d = st.text_input("Variant D:")
                cor_opt = st.selectbox("Düzgün Variant:", ["A", "B", "C", "D"])

                if st.form_submit_button("Quiz Paketini və Sualı Yadda Saxla"):
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO quiz_packages (class_level, title, difficulty, duration_minutes) VALUES (%s, %s, %s, %s) RETURNING id",
                            (q_class, q_title, q_diff, int(q_dur)))
                        pack_id = cur.fetchone()[0]
                        cur.execute(
                            "INSERT INTO quiz_questions (package_id, question_text, option_a, option_b, option_c, option_d, correct_option) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (pack_id, q_text, opt_a, opt_b, opt_c, opt_d, cor_opt))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Quiz və Sual uğurla əlavə olundu!")
                    except Exception as e:
                        st.error(e)

    # --- ŞAGİRD PANELİ ---
    else:
        curr_page = st.session_state.get("student_page", "Əsas səhifə")

        # 1. ƏSAS SƏHİFƏ / SCORE BOARD
        if curr_page == "Əsas səhifə":
            st.markdown(f"<h1>👋 Xoş gəldiniz, {st.session_state['full_name']}!</h1>", unsafe_allow_html=True)
            st.markdown("### 🏆 Sizin Nailiyyətlər Paneli (Score Board)")

            # Statistika məlumatlarının çəkilməsi
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT videos_watched, total_watch_minutes, quizzes_taken, total_correct, total_questions_answered FROM student_stats WHERE username = %s",
                    (st.session_state['username'],))
                s_stat = cur.fetchone()
                cur.close()
                conn.close()
            except Exception:
                s_stat = None

            v_count = s_stat[0] if s_stat else 0
            v_mins = s_stat[1] if s_stat else 0
            q_count = s_stat[2] if s_stat else 0
            t_correct = s_stat[3] if s_stat else 0
            t_answered = s_stat[4] if s_stat else 0

            accuracy_pct = round((t_correct / t_answered * 100), 1) if t_answered > 0 else 0.0

            col_sb1, col_sb2 = st.columns(2)
            with col_sb1:
                st.metric(label="📺 İzlənilən Video Sayı", value=f"{v_count} ədəd")
                st.metric(label="⏱️ Videolara Sərf Olunan Vaxt", value=f"{v_mins} dəqiqə")
            with col_sb2:
                st.metric(label="✍️ İşlənən Quiz Sayı", value=f"{q_count} ədəd")
                st.metric(label="🎯 Ümumi Düzgünlük Faizi", value=f"%{accuracy_pct}")

            st.write("---")
            st.info(
                "💡 Sol menyudan **Dərs Materialları** və ya **Quizlər və İmtahanlar** bölməsinə keçid edə bilərsiniz.")

        # 2. DƏRS MATERİALLARI SƏHİFƏSİ
        elif curr_page == "Materiallar":
            st.markdown("<h1>📚 Dərs Materialları və Mövzular</h1>", unsafe_allow_html=True)
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, title, content, file_url, video_url FROM lessons WHERE class_level = %s ORDER BY id DESC",
                    (st.session_state['class_level'],))
                lessons = cur.fetchall()
                cur.close()
                conn.close()

                if lessons:
                    for l in lessons:
                        with st.expander(f"📘 Mövzu: {l[1]}"):
                            if l[2]:
                                st.markdown(l[2])
                            if l[3]:
                                st.link_button("📄 PDF Faylı Aç", l[3])
                            if l[4]:
                                st.link_button("🎥 Video İzahı İzlə", l[4])
                                try:
                                    st.video(l[4])
                                except Exception:
                                    pass
                else:
                    st.warning("Bu sinif üçün material tapılmadı.")
            except Exception as e:
                st.error(e)

        # 3. QUİZLƏR VƏ İMTAHANLAR SƏHİFƏSİ
        elif curr_page == "Quizlər":
            st.markdown("<h1>✍️ Quizlər və İmtahan Modulu</h1>", unsafe_allow_html=True)
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, title, difficulty, duration_minutes FROM quiz_packages WHERE class_level = %s",
                            (st.session_state['class_level'],))
                packages = cur.fetchall()
                cur.close()
                conn.close()

                if packages:
                    pkg_dict = {p[0]: f"{p[1]} (Çətinlik: {p[2]} | Vaxt: {p[3]} dəq)" for p in packages}
                    selected_pkg = st.selectbox("Mövcud Quiz Paketini Seçin:", list(pkg_dict.keys()),
                                                format_func=lambda x: pkg_dict[x])

                    if selected_pkg:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option FROM quiz_questions WHERE package_id = %s",
                            (selected_pkg,))
                        questions = cur.fetchall()
                        cur.close()
                        conn.close()

                        if questions:
                            st.write(f"📌 **Sualların sayı:** {len(questions)} ədəd")

                            # Suallar arasında irəli-geri oxlar ilə naviqasiya üçün Session state
                            if "q_index" not in st.session_state:
                                st.session_state["q_index"] = 0
                            if "user_answers" not in st.session_state:
                                st.session_state["user_answers"] = {}

                            idx = st.session_state["q_index"]
                            q = questions[idx]

                            st.markdown(f"### Sual {idx + 1} / {len(questions)}")
                            st.write(f"**{q[1]}**")

                            opts = [f"A) {q[2]}", f"B) {q[3]}", f"C) {q[4]}", f"D) {q[5]}"]
                            curr_ans = st.session_state["user_answers"].get(q[0], None)

                            sel_opt = st.radio("Seçiminizi edin:", opts,
                                               index=opts.index(curr_ans) if curr_ans in opts else 0,
                                               key=f"q_radio_{q[0]}")
                            st.session_state["user_answers"][q[0]] = sel_opt

                            col_prev, col_next = st.columns(2)
                            with col_prev:
                                if idx > 0 and st.button("⬅️ Əvvəlki Sual"):
                                    st.session_state["q_index"] -= 1
                                    st.rerun()
                            with col_next:
                                if idx < len(questions) - 1 and st.button("Növbəti Sual ➡️"):
                                    st.session_state["q_index"] += 1
                                    st.rerun()

                            st.write("---")
                            if st.button("🎯 Quizi Tamamla və Nəticəni Hesabla", use_container_width=True):
                                correct_count = 0
                                total_q = len(questions)
                                answered_count = 0

                                for item in questions:
                                    qid = item[0]
                                    correct_letter = item[6].strip().upper()
                                    given = st.session_state["user_answers"].get(qid, "")
                                    if given:
                                        answered_count += 1
                                        if given.startswith(correct_letter):
                                            correct_count += 1

                                st.success(
                                    f"🎉 Quiz tamamlandı! Düzgün cavablar: {correct_count} / {total_q} (Cavablandırılmayanlar səhv sayıldı).")

                                # Statistikanı bazada yeniləmək
                                try:
                                    conn = get_db_connection()
                                    cur = conn.cursor()
                                    cur.execute(
                                        "SELECT id, quizzes_taken, total_correct, total_questions_answered FROM student_stats WHERE username = %s",
                                        (st.session_state['username'],))
                                    row = cur.fetchone()
                                    if row:
                                        cur.execute(
                                            "UPDATE student_stats SET quizzes_taken = quizzes_taken + 1, total_correct = total_correct + %s, total_questions_answered = total_questions_answered + %s WHERE username = %s",
                                            (correct_count, total_q, st.session_state['username']))
                                    else:
                                        cur.execute(
                                            "INSERT INTO student_stats (username, quizzes_taken, total_correct, total_questions_answered) VALUES (%s, 1, %s, %s)",
                                            (st.session_state['username'], correct_count, total_q))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                except Exception as ex:
                                    st.error(ex)
                        else:
                            st.info("Bu quiz paketində hələ sual yoxdur.")
                else:
                    st.warning("Aktiv quiz paketi mövcud deyil.")
            except Exception as e:
                st.error(e)