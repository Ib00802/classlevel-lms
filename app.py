import streamlit as st
import psycopg2
import hashlib

st.set_page_config(
    page_title="ClassLevel LMS Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stCard {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    h1, h2, h3 {
        color: #1e293b;
        font-family: 'Inter', sans-serif;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    </style>
""", unsafe_allow_html=True)


def get_db_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text


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

    cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS content TEXT;")
    cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS main_standard VARCHAR(255);")
    cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS sub_standard VARCHAR(255);")
    cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS file_url TEXT;")
    cur.execute("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS video_url TEXT;")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        id SERIAL PRIMARY KEY,
        lesson_id INT REFERENCES lessons(id) ON DELETE CASCADE,
        question_text TEXT NOT NULL,
        option_a VARCHAR(200),
        option_b VARCHAR(200),
        option_c VARCHAR(200),
        option_d VARCHAR(200),
        correct_option VARCHAR(1),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    try:
        cur.execute("ALTER TABLE quizzes ALTER COLUMN quiz_title DROP NOT NULL;")
    except Exception:
        pass

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
    st.error(f"❌ Supabase Qoşulma Xətası: {e}")

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

if st.session_state["logged_in"]:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['full_name']}")
        user_class = st.session_state.get('class_level', 5)
        role_text = "👨‍🏫 Müəllim (Admin)" if st.session_state[
                                                 'user_role'] == 'admin' else f"🎓 {user_class}-ci Sinif Şagirdi"
        st.info(role_text)
        st.write("---")
        if st.button("🚪 Çıxış Et", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["user_role"] = ""
            st.session_state["full_name"] = ""
            st.session_state["class_level"] = 5
            st.rerun()

    if st.session_state["user_role"] == "admin":
        st.markdown("<h1>👨‍🏫 Müəllim İdarəetmə Paneli</h1>", unsafe_allow_html=True)
        st.write("Sistemi idarə edin, yeni dərslər və imtahan sualları əlavə edin.")

        m_tab1, m_tab2, m_tab3 = st.tabs([
            "📊 Şagird Siyahısı",
            "➕ Yeni Dərs Əlavə Et",
            "❓ İmtahan Sualı Yarat"
        ])

        with m_tab1:
            st.subheader("🎓 Qeydiyyatdan Keçmiş Şagirdlər")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, full_name, username, student_code, class_level, created_at FROM users WHERE role = 'student' ORDER BY created_at DESC")
                students = cur.fetchall()
                cur.close()
                conn.close()

                if students:
                    st.dataframe(
                        [{"ID": s[0], "Ad Soyad": s[1], "Username": s[2], "Kod": s[3], "Sinif": f"{s[4]}-ci sinif",
                          "Tarix": s[5]} for s in students],
                        use_container_width=True
                    )
                else:
                    st.info("Hələ ki qeydiyyatdan keçən şagird yoxdur.")
            except Exception as ex:
                st.error(f"Xəta: {ex}")

        with m_tab2:
            st.subheader("📚 Yeni Dərs Modulu")
            with st.form("add_lesson_form"):
                lesson_title = st.text_input("Dərsin Adı / Mövzu:")
                target_class = st.selectbox("Sinif:", list(range(1, 12)), index=8)

                col_st1, col_st2 = st.columns(2)
                with col_st1:
                    main_std = st.text_input("Məzmun Standartı:")
                with col_st2:
                    sub_std = st.text_input("Alt Standart:")

                lesson_content = st.text_area("Dərs İzahı / Mətn:")

                col_lnk1, col_lnk2 = st.columns(2)
                with col_lnk1:
                    f_url = st.text_input("PDF / Fayl Linki:")
                with col_lnk2:
                    v_url = st.text_input("YouTube Video Linki:")

                st.write("")
                submit_lesson = st.form_submit_button("🚀 Dərsi Bazaya Əlavə Et", use_container_width=True)
                if submit_lesson:
                    if lesson_title.strip():
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("""
                                    INSERT INTO lessons (title, class_level, content, main_standard, sub_standard, file_url, video_url) 
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (lesson_title.strip(), target_class, lesson_content.strip(), main_std.strip(),
                                      sub_std.strip(), f_url.strip(), v_url.strip()))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"'{lesson_title}' uğurla əlavə olundu!")
                        except Exception as ex:
                            st.error(f"Xəta: {ex}")
                    else:
                        st.warning("Lütfən dərsin adını daxil edin.")

        with m_tab3:
            st.subheader("❓ İmtahan Sualı Əlavə Etmə Paneli")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, title, class_level FROM lessons ORDER BY id DESC")
                all_lessons = cur.fetchall()
                cur.close()
                conn.close()

                if all_lessons:
                    l_dict = {l[0]: f"{l[2]}-ci sinif: {l[1]}" for l in all_lessons}
                    q_lesson_id = st.selectbox("Hansı dərsə aid sualdır?", list(l_dict.keys()),
                                               format_func=lambda x: l_dict[x])

                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM quizzes WHERE lesson_id = %s", (int(q_lesson_id),))
                    current_q_count = cur.fetchone()[0]
                    cur.close()
                    conn.close()

                    next_q_num = current_q_count + 1
                    st.info(f"💡 Növbəti Sual: **Sual № {next_q_num}** (Mövcud sual sayı: {current_q_count})")

                    with st.form("add_quiz_form", clear_on_submit=True):
                        q_text = st.text_area(f"Sual {next_q_num} Mətni:")
                        op_a = st.text_input("Variant A:")
                        op_b = st.text_input("Variant B:")
                        op_c = st.text_input("Variant C:")
                        op_d = st.text_input("Variant D:")
                        correct_op = st.selectbox("Düzgün Variant:", ["A", "B", "C", "D"])

                        st.write("")
                        submit_q = st.form_submit_button(f"✨ Sual {next_q_num}-i Yadda Saxla", use_container_width=True)
                        if submit_q:
                            if q_text.strip():
                                try:
                                    conn = get_db_connection()
                                    cur = conn.cursor()

                                    cur.execute("""
                                            SELECT column_name FROM information_schema.columns 
                                            WHERE table_name='quizzes' AND column_name='quiz_title';
                                        """)
                                    has_quiz_title = cur.fetchone()
                                    selected_title = l_dict[q_lesson_id]

                                    if has_quiz_title:
                                        cur.execute("""
                                                INSERT INTO quizzes (lesson_id, quiz_title, question_text, option_a, option_b, option_c, option_d, correct_option)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                            """, (
                                        int(q_lesson_id), selected_title, q_text.strip(), op_a.strip(), op_b.strip(),
                                        op_c.strip(), op_d.strip(), correct_op))
                                    else:
                                        cur.execute("""
                                                INSERT INTO quizzes (lesson_id, question_text, option_a, option_b, option_c, option_d, correct_option)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                            """, (
                                        int(q_lesson_id), q_text.strip(), op_a.strip(), op_b.strip(), op_c.strip(),
                                        op_d.strip(), correct_op))

                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.success(f"🎉 Sual {next_q_num} əlavə olundu!")
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Xəta: {ex}")
                            else:
                                st.warning("Sual mətnini daxil edin.")
                else:
                    st.info("Əvvəlcə ən azı bir dərs əlavə etməlisiniz.")
            except Exception as ex:
                st.error(f"Xəta: {ex}")

    else:
        st.markdown(f"<h1>📖 Şagird Təhsil Portalı</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #64748b;'>Səviyyə: <b>{st.session_state['class_level']}-ci Sinif</b></p>",
                    unsafe_allow_html=True)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                    SELECT id, title, content, main_standard, sub_standard, file_url, video_url 
                    FROM lessons WHERE class_level = %s ORDER BY id DESC
                """, (st.session_state['class_level'],))
            available_lessons = cur.fetchall()
            cur.close()
            conn.close()

            if not available_lessons:
                st.warning(f"{st.session_state['class_level']}-ci sinif üçün hələ ki dərs materialı yoxdur.")
            else:
                lesson_dict = {l[0]: l[1] for l in available_lessons}
                selected_lesson_id = st.selectbox("📚 Öyrənmək istədiyiniz mövzunu seçin:", list(lesson_dict.keys()),
                                                  format_func=lambda x: lesson_dict[x])

                for l in available_lessons:
                    if l[0] == selected_lesson_id:
                        lid, ltitle, lcontent, lmain_std, lsub_std, lfile_url, lvideo_url = l

                        st.markdown("---")
                        st.markdown(f"### 📘 {ltitle}")

                        if lmain_std or lsub_std:
                            col_std1, col_std2 = st.columns(2)
                            with col_std1:
                                if lmain_std:
                                    st.markdown(f"📌 **Məzmun Standartı:** {lmain_std}")
                            with col_std2:
                                if lsub_std:
                                    st.markdown(f"🎯 **Alt Standart:** {lsub_std}")

                        if lcontent and lcontent.strip():
                            st.write("")
                            st.markdown(lcontent)

                        file_clean = lfile_url.strip() if lfile_url else ""
                        video_clean = lvideo_url.strip() if lvideo_url else ""

                        if file_clean or video_clean:
                            st.write("")
                            st.markdown("#### 📎 Dərs Resursları")
                            col_btn1, col_btn2 = st.columns(2)

                            with col_btn1:
                                if file_clean:
                                    st.link_button("📄 PDF Materialı Aç", file_clean, use_container_width=True)
                            with col_btn2:
                                if video_clean:
                                    st.link_button("🔗 Video İzahı İzlə", video_clean, use_container_width=True)

                            if video_clean and ("youtube.com" in video_clean or "youtu.be" in video_clean):
                                st.write("")
                                try:
                                    st.video(video_clean)
                                except Exception:
                                    pass

                questions = []
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    conn.rollback()

                    cur.execute("""
                            SELECT id, question_text, option_a, option_b, option_c, option_d 
                            FROM questions 
                            WHERE class_level = %s 
                            ORDER BY id ASC
                        """, (int(st.session_state['class_level']),))

                    questions = cur.fetchall()
                    cur.close()
                    conn.close()
                except Exception as ex:
                    questions = []

                if questions:
                    st.markdown("---")
                    st.markdown("### ✍️ Biliklərin Yoxlanılması (Quiz)")
                    with st.form("quiz_form"):
                        for idx, q in enumerate(questions, 1):
                            st.markdown(f"**Sual {idx}:** {q[1]}")
                            st.radio(f"Seçim ({idx}):", [f"A) {q[2]}", f"B) {q[3]}", f"C) {q[4]}", f"D) {q[5]}"],
                                     key=f"q_{q[0]}")
                            st.write("")

                        submit_quiz = st.form_submit_button("🎯 İmtahan Cavablarını Təqdim Et", use_container_width=True)
                        if submit_quiz:
                            st.success("🎉 Təbriklər! Cavablarınız uğurla qeydə alındı.")
                else:
                    st.info("Bu sinif üzrə aktiv imtahan sualı mövcud deyil.")
        except Exception as ex:
            st.error(f"Xəta baş verdi: {ex}")
else:
    col_center1, col_center2, col_center3 = st.columns([1, 2, 1])
    with col_center2:
        st.markdown("<h1 style='text-align: center; color: #4f46e5;'>🎓 ClassLevel LMS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>Müasir Təhsil və İmtahan İdarəetmə Platforması</p>",
                    unsafe_allow_html=True)
        st.write("")

        auth_tab1, auth_tab2 = st.tabs(["🔑 Sistemə Giriş", "📝 Yeni Qeydiyyat"])

        with auth_tab1:
            st.write("")
            username_input = st.text_input("İstifadəçi adı (Username):", key="login_user")
            password_input = st.text_input("Şifrə (Password):", type="password", key="login_pass")
            st.write("")

            if st.button("Daxil Ol", use_container_width=True):
                if username_input and password_input:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT full_name, username, password, role, class_level FROM users WHERE username = %s",
                            (username_input.strip(),))
                        user_data = cur.fetchone()
                        cur.close()
                        conn.close()

                        if user_data:
                            db_name, db_user, db_pass, db_role, db_class = user_data
                            if check_hashes(password_input, db_pass):
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = db_user
                                st.session_state["full_name"] = db_name
                                st.session_state["user_role"] = db_role
                                st.session_state["class_level"] = int(db_class) if db_class else 5

                                st.success(f"Xoş gəldiniz, {db_name}!")
                                st.rerun()
                            else:
                                st.error("Şifrə yanlışdır!")
                        else:
                            st.error("Bu istifadəçi adı tapılmadı!")
                    except Exception as ex:
                        st.error(f"Giriş zamanı xəta: {ex}")
                else:
                    st.warning("Zəhmət olmasa xanaları doldurun.")

        with auth_tab2:
            st.write("")
            reg_fullname = st.text_input("Ad və Soyadınız:", placeholder="Məs: Əli Əliyev", key="reg_fn")
            reg_username = st.text_input("İstifadəçi Adı (Username):", placeholder="Məs: ali_aliyev", key="reg_un")
            reg_password = st.text_input("Şifrə təyin edin:", type="password", key="reg_pw")
            reg_class = st.selectbox("Sinfinizi seçin:", list(range(1, 12)), index=8, key="reg_cl")
            reg_code = st.text_input("Müəllimin verdiyi 3 rəqəmli Şagird Kodu:", max_chars=3, placeholder="Məs: 101",
                                     key="reg_cd")
            st.write("")

            if st.button("Qeydiyyatı Tamamla", use_container_width=True):
                if reg_fullname and reg_username and reg_password and reg_code:
                    if len(reg_code.strip()) != 3 or not reg_code.strip().isdigit():
                        st.error("Şagird Kodu dəqiq 3 rəqəmdən ibarət olmalıdır!")
                    else:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()

                            cur.execute("SELECT id FROM users WHERE username = %s", (reg_username.strip(),))
                            if cur.fetchone():
                                st.error("Bu istifadəçi adı artıq götürülüb!")
                                cur.close()
                                conn.close()
                                st.stop()

                            cur.execute("SELECT id FROM users WHERE student_code = %s", (reg_code.strip(),))
                            if cur.fetchone():
                                st.error("Bu 3 rəqəmli Kodla artıq qeydiyyat keçilib!")
                                cur.close()
                                conn.close()
                                st.stop()

                            hashed_pw = make_hashes(reg_password)
                            cur.execute(
                                "INSERT INTO users (full_name, username, password, role, student_code, class_level) VALUES (%s, %s, %s, %s, %s, %s)",
                                (reg_fullname.strip(), reg_username.strip(), hashed_pw, 'student', reg_code.strip(),
                                 int(reg_class))
                            )
                            conn.commit()
                            cur.close()
                            conn.close()

                            st.success("🎉 Qeydiyyat uğurla tamamlandı! İndi daxil ola bilərsiniz.")
                        except Exception as ex:
                            st.error(f"Qeydiyyat xətası: {ex}")
                else:
                    st.warning("Lütfən bütün xanaları doldurun.")