import streamlit as st
import psycopg2
import pandas as pd

# Səhifə konfiqurasiyası
st.set_page_config(page_title="ClassLevel LMS", page_icon="🎓", layout="wide")


# ==========================================
# BAZA İLƏ BAĞLANTI FUNKSİYASI (SUPABASE SECRETS)
# ==========================================
def get_db_connection():
    try:
        if "postgres" in st.secrets:
            return psycopg2.connect(
                host=st.secrets["postgres"]["host"],
                database=st.secrets["postgres"]["database"],
                user=st.secrets["postgres"]["user"],
                password=st.secrets["postgres"]["password"],
                port=st.secrets["postgres"]["port"]
            )
        else:
            return psycopg2.connect(
                host=st.secrets["host"],
                database=st.secrets["database"],
                user=st.secrets["user"],
                password=st.secrets["password"],
                port=st.secrets["port"]
            )
    except Exception as e:
        try:
            return psycopg2.connect(st.secrets["postgres"]["url"])
        except:
            raise e


# Session State tənzimləmələri
if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# GİRİŞ VƏ QEYDİYYAT SƏHİFƏSİ
# ==========================================
if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center;'>🎓 ClassLevel LMS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Müasir Təhsil və İdarəetmə Portalı</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Sistemə Giriş", "📝 Yeni Qeydiyyat"])

        with tab1:
            username = st.text_input("İstifadəçi adı:", key="login_user")
            password = st.text_input("Şifrə:", type="password", key="login_pass")

            if st.button("Daxil Ol", use_container_width=True):
                if username and password:
                    # 1. Təhlükəsizlik / Əsas Admin yoxlaması (Hardcoded fallback)
                    if username.strip() == "admin" and password.strip() == "Muellim2026!":
                        st.session_state.user = {
                            "id": 0,
                            "full_name": "Sistem Administratoru",
                            "username": "admin",
                            "role": "teacher",
                            "class_level": 0
                        }
                        st.success("Uğurla daxil oldunuz!")
                        st.rerun()
                    else:
                        # 2. Bazadan istifadəçilərin yoxlanması
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                "SELECT id, full_name, username, role, class_level FROM users WHERE username = %s AND password = %s",
                                (username.strip(), password.strip())
                            )
                            user_data = cur.fetchone()
                            cur.close()
                            conn.close()

                            if user_data:
                                st.session_state.user = {
                                    "id": user_data[0],
                                    "full_name": user_data[1],
                                    "username": user_data[2],
                                    "role": user_data[3],
                                    "class_level": user_data[4]
                                }
                                st.success("Uğurla daxil oldunuz!")
                                st.rerun()
                            else:
                                st.error("İstifadəçi adı və ya şifrə yanlışdır.")
                        except Exception as e:
                            st.error(f"Sistem xətası: {e}")
                else:
                    st.warning("Məlumatları tam doldurun.")

        with tab2:
            st.info("Yeni şagird qeydiyyatı üçün məlumatları daxil edin:")
            new_fullname = st.text_input("Ad Soyad:")
            new_user = st.text_input("İstifadəçi adı (Username):")
            new_pass = st.text_input("Şifrə təyin edin:", type="password")
            new_class = st.selectbox("Sinif seçin:", list(range(1, 12)), index=8)
            new_code = st.text_input("Şagird Kodu (Könüllü):")

            if st.button("Qeydiyyatı Tamamla", use_container_width=True):
                if new_fullname and new_user and new_pass:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO users (full_name, username, password, role, student_code, class_level) VALUES (%s, %s, %s, %s, %s, %s)",
                            (new_fullname.strip(), new_user.strip(), new_pass.strip(), 'student', new_code.strip(),
                             new_class)
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Qeydiyyat uğurla tamamlandı! İndi daxil ola bilərsiniz.")
                    except Exception as e:
                        st.error(f"Qeydiyyat zamanı xəta: {e}")
                else:
                    st.warning("Zəhmət olmasa tələb olunan xanaları doldurun.")
# ==========================================
# İSTİFADƏÇİ SİSTEMƏ DAXİL OLDUQDAN SONRA
# ==========================================
else:
    # --------------------------------------
    # HİSSƏ A: MÜƏLLİM PANELİ (GENİŞLƏNDİRİLMİŞ)
    # --------------------------------------
    if st.session_state.user["role"] == "teacher":
        st.title("👨‍🏫 Müəllim İdarəetmə Paneli")

        st.sidebar.markdown(f"### 👨‍🏫 {st.session_state.user['full_name']}")
        st.sidebar.caption("Status: Müəllim / Admin")

        if st.sidebar.button("🚪 Çıxış Et", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        m_t1, m_t2, m_t3 = st.tabs(["👥 Şagirdlər", "📚 Materialların İdarə Edilməsi", "📝 Quiz Paketi və Suallar"])

        # --- TAB 1: ŞAGİRD LİSTİ ---
        with m_t1:
            st.subheader("👥 Qeydiyyatdan Keçmiş Şagirdlər")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, full_name, username, student_code, class_level FROM users WHERE role = 'student' ORDER BY class_level, full_name")
                students_data = cur.fetchall()
                cur.close()
                conn.close()

                if students_data:
                    df_students = pd.DataFrame(students_data,
                                               columns=["ID", "Ad Soyad", "İstifadəçi Adı", "Şagird Kodu", "Sinif"])
                    st.dataframe(df_students, use_container_width=True, hide_index=True)
                else:
                    st.info("Hələ ki sistemdə qeydiyyatdan keçmiş şagird yoxdur.")
            except Exception as e:
                st.error(f"Şagird siyahısı yüklənərkən xəta yarandı: {e}")

        # --- TAB 2: MATERİALLARIN İDARƏ EDİLMƏSİ (GENİŞ) ---
        with m_t2:
            st.subheader("📚 Dərs Materiallarının Əlavə Olunması və İdarəsi")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS materials (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255),
                        class_level INT,
                        file_link TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                cur.close()
                conn.close()
            except:
                pass

            with st.form("add_material_form_advanced", clear_on_submit=True):
                st.markdown("### ➕ Yeni Material Yerləşdir")
                mat_title = st.text_input("Materialın Adı / Mövzu Başlığı:")
                mat_class = st.selectbox("Hansı Sinif Üçün:", list(range(1, 12)), index=8, key="mat_cl_adv")
                mat_link = st.text_input("Materialın Keçid Linki (Google Drive, YouTube, PDF URL və s.):")

                if st.form_submit_button("Materialı Bazaya Əlavə Et"):
                    if mat_title and mat_link:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("INSERT INTO materials (title, class_level, file_link) VALUES (%s, %s, %s)",
                                        (mat_title.strip(), int(mat_class), mat_link.strip()))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success("Material uğurla əlavə olundu!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Xəta baş verdi: {e}")
                    else:
                        st.warning("Zəhmət olmasa başlıq və link sahələrini doldurun.")

            st.write("---")
            st.markdown("### 📋 Hazırda Sistemdə Olan Materiallar")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, title, class_level, file_link, created_at FROM materials ORDER BY class_level, id DESC")
                mats = cur.fetchall()
                cur.close()
                conn.close()

                if mats:
                    df_mats = pd.DataFrame(mats, columns=["ID", "Mövzu / Başlıq", "Sinif", "Keçid Linki", "Tarix"])
                    st.dataframe(df_mats, use_container_width=True, hide_index=True)
                else:
                    st.info("Hələ ki heç bir material əlavə olunmayıb.")
            except Exception as e:
                st.error(f"Materiallar yüklənərkən xəta: {e}")

        # --- TAB 3: QUİZ PAKETİ VƏ SUALLAR (GENİŞ) ---
        with m_t3:
            st.subheader("📝 Quiz Paketi Yaratmaq və Sual Əlavə Etmək")

            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_packages (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255),
                        class_level INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS quizzes (
                        id SERIAL PRIMARY KEY,
                        quiz_package_id INT,
                        question_text TEXT,
                        option_a TEXT,
                        option_b TEXT,
                        option_c TEXT,
                        option_d TEXT,
                        correct_option VARCHAR(5)
                    )
                """)
                conn.commit()
                cur.close()
                conn.close()
            except:
                pass

            sub_tab1, sub_tab2 = st.tabs(["📦 Yeni Paket Yarat", "➕ Paketet Sual Əlavə Et"])

            with sub_tab1:
                with st.form("create_quiz_pkg_adv"):
                    pkg_title = st.text_input("Quiz Paketinin Adı (məs: 9-cu Sinif Həndəsə Sınaq 1):")
                    pkg_class = st.selectbox("Aid Olduğu Sinif:", list(range(1, 12)), index=8, key="pkg_cl_adv")

                    if st.form_submit_button("Paketi Yarat"):
                        if pkg_title:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute("INSERT INTO quiz_packages (title, class_level) VALUES (%s, %s)",
                                            (pkg_title.strip(), pkg_class))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(
                                    "Quiz paketi uğurla yaradıldı! İndi 'Paketə Sual Əlavə Et' bölməsindən suallar əlavə edə bilərsiniz.")
                            except Exception as e:
                                st.error(f"Xəta: {e}")
                        else:
                            st.warning("Paket adını daxil edin.")

            with sub_tab2:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT id, title, class_level FROM quiz_packages ORDER BY id DESC")
                    packages = cur.fetchall()
                    cur.close()
                    conn.close()

                    if not packages:
                        st.info("Əvvəlcə 'Yeni Paket Yarat' bölməsindən quiz paketi yaradın.")
                    else:
                        pkg_dict = {f"{p[1]} ({p[2]}-ci sinif)": p[0] for p in packages}
                        selected_pkg_name = st.selectbox("Sual əlavə olunacaq paketi seçin:", list(pkg_dict.keys()))
                        target_pkg_id = pkg_dict[selected_pkg_name]

                        with st.form("add_question_form", clear_on_submit=True):
                            st.markdown("#### Sual Təfərrüatları")
                            q_text = st.text_area("Sualın mətni:")
                            opt_a = st.text_input("A variantı:")
                            opt_b = st.text_input("B variantı:")
                            opt_c = st.text_input("C variantı:")
                            opt_d = st.text_input("D variantı:")
                            correct_opt = st.selectbox("Doğru Cavab:", ["A", "B", "C", "D"])

                            if st.form_submit_button("Sualı Əlavə Et"):
                                if q_text and opt_a and opt_b and opt_c and opt_d:
                                    try:
                                        conn = get_db_connection()
                                        cur = conn.cursor()
                                        cur.execute("""
                                            INSERT INTO quizzes (quiz_package_id, question_text, option_a, option_b, option_c, option_d, correct_option)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        """, (
                                        target_pkg_id, q_text.strip(), opt_a.strip(), opt_b.strip(), opt_c.strip(),
                                        opt_d.strip(), correct_opt))
                                        conn.commit()
                                        cur.close()
                                        conn.close()
                                        st.success("Sual paketə uğurla əlavə olundu!")
                                    except Exception as e:
                                        st.error(f"Xəta: {e}")
                                else:
                                    st.warning("Bütün xanaları doldurun.")
                except Exception as e:
                    st.error(f"Paketlər yüklənərkən xəta: {e}")

    # --------------------------------------
    # HİSSƏ B: ŞAGİRD PANELİ
    # --------------------------------------
    elif st.session_state.user["role"] == "student":
        student_class = st.session_state.user.get("class_level", 9)
        student_id = st.session_state.user["id"]

        st.sidebar.markdown(f"### 🎓 {st.session_state.user['full_name']}")
        st.sidebar.info(f"📌 {student_class}-cı Sinif Şagirdi")

        s_menu = st.sidebar.radio(
            "Menyu",
            ["🏠 Əsas Səhifə / Score Board", "📚 Dərs Materialları", "📝 Quizlər və İmtahanlar"],
            label_visibility="collapsed"
        )

        st.sidebar.write("---")
        if st.sidebar.button("🚪 Çıxış Et", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        # --- 1. SCORE BOARD ---
        if s_menu == "🏠 Əsas Səhifə / Score Board":
            st.header("🏠 Xoş Gəldiniz!")
            st.write(f"Salam, **{st.session_state.user['full_name']}**!")

            st.write("---")
            st.subheader("🏆 Liderlər Lövhəsi (Score Board)")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_results (
                        id SERIAL PRIMARY KEY,
                        student_id INT,
                        package_id INT,
                        score FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()

                cur.execute("""
                    SELECT u.full_name, u.class_level, COALESCE(SUM(r.score), 0) as total_score, COUNT(r.id) as total_quizzes
                    FROM users u
                    LEFT JOIN quiz_results r ON u.id = r.student_id
                    WHERE u.role = 'student'
                    GROUP BY u.id, u.full_name, u.class_level
                    ORDER BY total_score DESC, total_quizzes DESC
                """)
                scores = cur.fetchall()
                cur.close()
                conn.close()

                if scores:
                    df_scores = pd.DataFrame(scores, columns=["Şagird", "Sinif", "Ümumi Bal", "İşlənmiş Quiz Sayı"])
                    st.dataframe(df_scores, use_container_width=True, hide_index=True)
                else:
                    st.info("Hələ ki heç bir nəticə qeydə alınmayıb.")
            except Exception as e:
                st.info("Nəticələr lövhəsi hələ ki hazırlanır.")

        # --- 2. DƏRS MATERİALLARI ---
        elif s_menu == "📚 Dərs Materialları":
            st.header("📚 Dərs Materialları")
            st.write(f"**{student_class}-cı sinif** üçün əlçatan materiallar:")

            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT title, file_link, created_at FROM materials WHERE class_level = %s ORDER BY id DESC",
                    (student_class,))
                materials = cur.fetchall()
                cur.close()
                conn.close()

                if materials:
                    for mat_title, mat_link, mat_date in materials:
                        with st.container():
                            st.markdown(f"#### 📖 {mat_title}")
                            st.markdown(f"[📥 Materialı Aç / Yüklə]({mat_link})")
                            st.caption(f"Yüklənmə tarixi: {mat_date}")
                            st.write("---")
                else:
                    st.info(f"{student_class}-cı sinif üçün hələ ki dərs materialı əlavə olunmayıb.")
            except Exception as e:
                st.error(f"Materiallar yüklənərkən xəta: {e}")

        # --- 3. QUİZLƏR VƏ İMTAHANLAR ---
        elif s_menu == "📝 Quizlər və İmtahanlar":
            st.header("📝 Quizlər və İmtahanlar")

            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, title FROM quiz_packages WHERE class_level = %s ORDER BY id DESC",
                            (student_class,))
                packages = cur.fetchall()

                if not packages:
                    st.info(f"{student_class}-cı sinif üçün aktiv quiz paketi tapılmadı.")
                    cur.close()
                    conn.close()
                else:
                    pkg_options = {pkg[1]: pkg[0] for pkg in packages}
                    selected_pkg_title = st.selectbox("İşləmək istədiyiniz quizi seçin:", list(pkg_options.keys()))
                    selected_pkg_id = pkg_options[selected_pkg_title]

                    cur.execute("""
                        SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option 
                        FROM quizzes 
                        WHERE quiz_package_id = %s 
                        ORDER BY id ASC
                    """, (selected_pkg_id,))

                    questions = cur.fetchall()
                    cur.close()
                    conn.close()

                    if not questions:
                        st.warning("Bu paketdə hələ ki sual mövcud deyil.")
                    else:
                        with st.form("quiz_submit_form_adv"):
                            user_answers = {}
                            st.markdown(f"### 📋 {selected_pkg_title}")

                            for idx, q in enumerate(questions, 1):
                                q_id, q_text, opt_a, opt_b, opt_c, opt_d, corr = q
                                st.write(f"**{idx}. {q_text}**")

                                options = {
                                    f"A) {opt_a}": "A",
                                    f"B) {opt_b}": "B",
                                    f"C) {opt_c}": "C",
                                    f"D) {opt_d}": "D"
                                }

                                choice = st.radio(f"Cavabınız (Sual {idx}):", list(options.keys()), key=f"q_{q_id}",
                                                  label_visibility="collapsed")
                                user_answers[q_id] = (options[choice], corr)
                                st.write("---")

                            if st.form_submit_button("İmtahanı Tamamla"):
                                score = 0
                                total_q = len(questions)
                                for q_id, (ans, corr) in user_answers.items():
                                    if ans == corr:
                                        score += 1

                                final_score = round((score / total_q) * 100, 1)

                                try:
                                    conn = get_db_connection()
                                    cur = conn.cursor()
                                    cur.execute("""
                                        CREATE TABLE IF NOT EXISTS quiz_results (
                                            id SERIAL PRIMARY KEY,
                                            student_id INT,
                                            package_id INT,
                                            score FLOAT,
                                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                        )
                                    """)
                                    cur.execute(
                                        "INSERT INTO quiz_results (student_id, package_id, score) VALUES (%s, %s, %s)",
                                        (student_id, selected_pkg_id, final_score))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.balloons()
                                    st.success(
                                        f"İmtahan başa çatdı! Nəticəniz: {final_score}% ({total_q} sualdan {score} düzgün)")
                                except Exception as e:
                                    st.error(f"Nəticə yadda saxlanılarkən xəta: {e}")
            except Exception as e:
                st.error(f"Quizlər yüklənərkən xəta: {e}")