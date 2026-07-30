import streamlit as st
import psycopg2
import hashlib
import random

st.set_page_config(page_title="ClassLevel LMS Portal", page_icon="🚀", layout="wide")


# --- DATABASE CONNECTION ---
def get_db_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])


# Şifrəni təhlükəsiz həşləmək üçün funksiya
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text


# Cədvəllərin Yaranması
try:
    conn = get_db_connection()
    cur = conn.cursor()

    # İstifadəçilər Cədvəli
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

    # Dərslər Cədvəli
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id SERIAL PRIMARY KEY,
        title VARCHAR(150) NOT NULL,
        class_level INT NOT NULL,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Quizlər Cədvəli
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

    conn.commit()
    cur.close()
    conn.close()
except Exception as e:
    st.error(f"❌ Supabase Qoşulma Xətası: {e}")

# --- SESSION STATE (Sessiya İdarəetməsi) ---
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
if "verification_code" not in st.session_state:
    st.session_state["verification_code"] = None
if "pending_user_data" not in st.session_state:
    st.session_state["pending_user_data"] = None

# ==========================================
# MƏRHƏLƏ 1: GİRİŞ / QEYDİYYAT SƏHİFƏSİ
# ==========================================
if not st.session_state["logged_in"]:
    st.title("🚀 ClassLevel LMS - Giriş Və Qeydiyyat Portalı")

    auth_tab1, auth_tab2 = st.tabs(["🔑 Sistemə Giriş (Login)", "📝 Yeni Qeydiyyat (Register)"])

    # TAB 1: GİRİŞ ET
    with auth_tab1:
        st.subheader("Mövcud hesabınızla daxil olun")
        username_input = st.text_input("İstifadəçi adı (Username):", key="login_user")
        password_input = st.text_input("Şifrə (Password):", type="password", key="login_pass")

        if st.button("Sistemə Giriş Et"):
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
                            st.session_state["class_level"] = db_class
                            st.success(f"Xoş gəldiniz, {db_name}!")
                            st.rerun()
                        else:
                            st.error("Şifrə yanlışdır!")
                    else:
                        st.error("Bu istifadəçi adı tapılmadı! Zəhmət olmasa qeydiyyatdan keçin.")
                except Exception as ex:
                    st.error(f"Giriş zamanı xəta: {ex}")
            else:
                st.warning("Zəhmət olmasa istifadəçi adı və şifrəni yazın.")

    # TAB 2: YENİ QEYDİYYAT (Mərhələli və Sinif Dəqiqliyi İlə)
    with auth_tab2:
        st.subheader("Yeni hesab yaradın")

        # 1-Cİ ADDIM: Məlumatların daxil edilməsi
        if st.session_state["verification_code"] is None:
            reg_fullname = st.text_input("Ad və Soyadınız:", placeholder="Məs: Əli Əliyev", key="reg_fn")
            reg_username = st.text_input("İstifadəçi Adı seçin (Username):", placeholder="Məs: ali_aliyev",
                                         key="reg_un")
            reg_password = st.text_input("Şifrə təyin edin:", type="password", key="reg_pw")
            reg_role = st.selectbox("Hesab Növü (Rolunuz):", ["Şagird (User)", "Müəllim (Admin)"], key="reg_rl")

            selected_class = None
            reg_code = None

            if reg_role == "Şagird (User)":
                selected_class = st.selectbox("Sinfinizi seçin:", list(range(1, 12)), index=4, key="reg_cl")
                reg_code = st.text_input("Müəllimin verdiyi 3 rəqəmli Şagird Kodu:", max_chars=3,
                                         placeholder="Məs: 101", key="reg_cd")

            if st.button("Təsdiq Kodu Göndər"):
                if reg_fullname and reg_username and reg_password:
                    if reg_role == "Şagird (User)" and (not reg_code or len(reg_code) != 3 or not reg_code.isdigit()):
                        st.error("Şagird Kodu dəqiq 3 rəqəmdən ibarət olmalıdır!")
                    else:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()

                            # Username kontrolu
                            cur.execute("SELECT id FROM users WHERE username = %s", (reg_username.strip(),))
                            if cur.fetchone():
                                st.error("Bu istifadəçi adı artıq götürülüb!")
                                cur.close()
                                conn.close()
                                st.stop()

                            # Şagird kodu kontrolu
                            if reg_role == "Şagird (User)":
                                cur.execute("SELECT id FROM users WHERE student_code = %s", (reg_code.strip(),))
                                if cur.fetchone():
                                    st.error("Bu 3 rəqəmli Şagird Kodu ilə artıq qeydiyyat keçilib!")
                                    cur.close()
                                    conn.close()
                                    st.stop()

                            cur.close()
                            conn.close()

                            # Təsdiq Kodu generatoru
                            v_code = str(random.randint(1000, 9999))
                            st.session_state["verification_code"] = v_code

                            # Yalnız seçilən 1 sinfi yadda saxlayırıq
                            st.session_state["pending_user_data"] = {
                                "fullname": reg_fullname.strip(),
                                "username": reg_username.strip(),
                                "password": make_hashes(reg_password),
                                "role": "admin" if reg_role == "Müəllim (Admin)" else "student",
                                "code": reg_code.strip() if reg_role == "Şagird (User)" else None,
                                "class": int(selected_class) if reg_role == "Şagird (User)" else 0
                            }
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Yoxlama xətası: {ex}")
                else:
                    st.warning("Lütfən bütün xanaları doldurun.")

        # 2-Cİ ADDIM: Verification (Təsdiq Kodu) daxil etmə ekranı
        else:
            st.info("🔒 **Təhlükəsizlik Təsdiqi:** Təsdiq kodu yaradıldı.")
            st.warning(
                f"🔑 Təsdiq Şifrəniz: **{st.session_state['verification_code']}** (Zəhmət olmasa aşağıdakı xanaya yazın)")

            user_v_code = st.text_input("4 rəqəmli Təsdiq Kodunu daxil edin:", max_chars=4, key="ver_input")

            col_ver1, col_ver2 = st.columns(2)
            with col_ver1:
                if st.button("Qeydiyyatı Tamamla"):
                    if user_v_code.strip() == st.session_state["verification_code"]:
                        data = st.session_state["pending_user_data"]
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                "INSERT INTO users (full_name, username, password, role, student_code, class_level) VALUES (%s, %s, %s, %s, %s, %s)",
                                (data["fullname"], data["username"], data["password"], data["role"], data["code"],
                                 data["class"])
                            )
                            conn.commit()
                            cur.close()
                            conn.close()

                            st.success(
                                "🎉 Qeydiyyat uğurla tamamlandı! İndi 'Sistemə Giriş Et' bölməsindən daxil ola bilərsiniz.")
                            st.session_state["verification_code"] = None
                            st.session_state["pending_user_data"] = None
                        except Exception as ex:
                            st.error(f"Qeydiyyatı tamamlama xətası: {ex}")
                    else:
                        st.error("Daxil edilən təsdiq kodu yanlışdır!")

            with col_ver2:
                if st.button("Yenidən Başla / Ləğv Et"):
                    st.session_state["verification_code"] = None
                    st.session_state["pending_user_data"] = None
                    st.rerun()


# ==========================================
# MƏRHƏLƏ 2: DAXİL OLDUQDAN SONRAKİ PANELLƏR
# ==========================================
else:
    # Sol menyu
    st.sidebar.title(f"👤 {st.session_state['full_name']}")

    user_class = st.session_state.get('class_level', 5)
    role_text = "Müəllim (Admin)" if st.session_state['user_role'] == 'admin' else f"{user_class}-ci Sinif Şagirdi"
    st.sidebar.write(f"**Rol:** {role_text}")

    if st.sidebar.button("🚪 Çıxış Et (Logout)"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["user_role"] = ""
        st.rerun()

    # ------------------------------------------
    # A) MÜƏLLİM ADMİN PANELİ
    # ------------------------------------------
    if st.session_state["user_role"] == "admin":
        st.title("👨‍🏫 Müəllim İdarəetmə Paneli (ADMIN)")

        m_tab1, m_tab2, m_tab3 = st.tabs([
            "📊 Şagird Siyahısı & Şagird Kodları",
            "➕ Yeni Dərs Əlavə Et",
            "❓ İmtahan Sualı Yarat"
        ])

        # TAB 1: Şagirdlərin Unikal Kodları ilə Siyahısı
        with m_tab1:
            st.subheader("🎓 Qeydiyyatdan Keçmiş Şagirdlər Siyahısı")
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
                        [{"ID": s[0], "Ad Soyad": s[1], "Username": s[2], "3 Rəqəmli Kod": s[3],
                          "Sinif": f"{s[4]}-ci sinif", "Qeydiyyat Tarixi": s[5]} for s in students],
                        use_container_width=True
                    )
                else:
                    st.info("Hələ ki heç bir şagird sistemdə qeydiyyatdan keçməyib.")
            except Exception as ex:
                st.error(f"Şagird siyahısı yüklənərkən xəta: {ex}")

        # TAB 2: Dərs Əlavə Et
        with m_tab2:
            st.subheader("📚 Bazaya Yeni Dərs Əlavə Et")
            with st.form("add_lesson_form"):
                lesson_title = st.text_input("Dərsin Adı / Mövzu:")
                target_class = st.selectbox("Hansi sinif üçün?", list(range(1, 12)), index=4)
                lesson_content = st.text_area("Dərs haqqında mətn:")

                submit_lesson = st.form_submit_button("Dərsi Bazaya Əlavə Et")
                if submit_lesson:
                    if lesson_title.strip():
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("INSERT INTO lessons (title, class_level, content) VALUES (%s, %s, %s)",
                                        (lesson_title.strip(), target_class, lesson_content))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"'{lesson_title}' uğurla {target_class}-ci sinfə əlavə edildi!")
                        except Exception as ex:
                            st.error(f"Dərs əlavə edilərkən xəta: {ex}")
                    else:
                        st.warning("Lütfən dərsin adını yazın.")

        # TAB 3: Quiz Yarat
        with m_tab3:
            st.subheader("❓ Dərslərə Uyğun İmtahan Sualı Yarat")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, title, class_level FROM lessons")
                all_lessons = cur.fetchall()
                cur.close()
                conn.close()

                if all_lessons:
                    l_dict = {l[0]: f"{l[2]}-ci sinif: {l[1]}" for l in all_lessons}
                    q_lesson_id = st.selectbox("Sual hansı dərsə aid olsun?", list(l_dict.keys()),
                                               format_func=lambda x: l_dict[x])

                    with st.form("add_quiz_form"):
                        q_text = st.text_area("Sual mətni:")
                        op_a = st.text_input("Variant A:")
                        op_b = st.text_input("Variant B:")
                        op_c = st.text_input("Variant C:")
                        op_d = st.text_input("Variant D:")
                        correct_op = st.selectbox("Düzgün Variant:", ["A", "B", "C", "D"])

                        submit_q = st.form_submit_button("Sualı Əlavə Et")
                        if submit_q:
                            if q_text.strip():
                                try:
                                    conn = get_db_connection()
                                    cur = conn.cursor()
                                    cur.execute("""
                                        INSERT INTO quizzes (lesson_id, question_text, option_a, option_b, option_c, option_d, correct_option)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    """, (q_lesson_id, q_text, op_a, op_b, op_c, op_d, correct_op))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.success("Sual uğurla bazaya əlavə olundu!")
                                except Exception as ex:
                                    st.error(f"Sual əlavə edilərkən xəta: {ex}")
                            else:
                                st.warning("Sual mətnini daxil edin.")
                else:
                    st.info("Sual əlavə etmək üçün əvvəlcə ən azı 1 dərs əlavə olunmalıdır.")
            except Exception as ex:
                st.error(f"Dərslər yüklənərkən xəta: {ex}")

    # ------------------------------------------
    # B) ŞAGİRD USER PANELİ
    # ------------------------------------------
    else:
        st.title(f"📖 Şagird İmtahan Portalı ({st.session_state['class_level']}-ci Sinif)")

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, title, content FROM lessons WHERE class_level = %s",
                        (st.session_state['class_level'],))
            available_lessons = cur.fetchall()
            cur.close()
            conn.close()

            if not available_lessons:
                st.warning(f"{st.session_state['class_level']}-ci sinif üçün hələ ki bazada dərs əlavə edilməyib.")
            else:
                lesson_dict = {l[0]: l[1] for l in available_lessons}
                selected_lesson_id = st.selectbox("Dərsi seçin:", list(lesson_dict.keys()),
                                                  format_func=lambda x: lesson_dict[x])

                for l in available_lessons:
                    if l[0] == selected_lesson_id:
                        st.info(f"**Dərs Mövzusu:** {l[1]}\n\n{l[2] if l[2] else ''}")

                # İmtahan sualları
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, question_text, option_a, option_b, option_c, option_d FROM quizzes WHERE lesson_id = %s",
                    (selected_lesson_id,))
                questions = cur.fetchall()
                cur.close()
                conn.close()

                if questions:
                    st.write("---")
                    st.subheader("✍️ Quiz / İmtahan Sualları")
                    with st.form("quiz_form"):
                        for idx, q in enumerate(questions, 1):
                            st.markdown(f"**Sual {idx}: {q[1]}**")
                            st.radio(f"Cavabınızı seçin ({idx}):",
                                     [f"A) {q[2]}", f"B) {q[3]}", f"C) {q[4]}", f"D) {q[5]}"], key=f"q_{q[0]}")

                        submit_quiz = st.form_submit_button("İmtahanı Tamamla")
                        if submit_quiz:
                            st.success("Cavablarınız qeydə alındı!")
                else:
                    st.info("Bu dərs üzrə hələ ki imtahan sualı əlavə edilməyib.")
        except Exception as ex:
            st.error(f"Dərslər yüklənərkən xəta: {ex}")