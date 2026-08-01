import hashlib
import pandas as pd
import psycopg2
import streamlit as st

# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------
# Secrets-dən oxunur, yoxdursa birbaşa təyin edilən DB_URL-ə düşür
# .streamlit/secrets.toml faylından oxuyur, yoxdursa Supabase URL-ni istifadə edir:
DB_URL = st.secrets.get("DB_URL", "postgresql://postgres:Muellim2026!@db.[PROJECT-REF].supabase.co:5432/postgres")


def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        st.error(f"Verilənlər bazasına qoşulma xətası: {e}")
        return None


def hash_password(password):
    return hashlib.md5(password.strip().encode()).hexdigest()


# ---------------------------------------------------------
# PAGE CONFIGURATION & STYLES
# ---------------------------------------------------------
st.set_page_config(page_title="Təhsil Portalı", page_icon="🎓", layout="wide")

# Session state initialization
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------------------------------------------------
# AUTHENTICATION SCREEN
# ---------------------------------------------------------
if not st.session_state.user:
    st.title("🎓 Təhsil Portalı və İmtahan Sistemi")

    tab1, tab2 = st.tabs(["🔑 Sistemə Giriş", "📝 Yeni Qeydiyyat"])

    with tab1:
        st.subheader("Giriş Parametrləri")
        login_user = st.text_input("İstifadəçi adı:", key="login_user")
        login_pass = st.text_input("Şifrə:", type="password", key="login_pass")

        if st.button("Daxil Ol", use_container_width=True):
            if login_user and login_pass:
                conn = get_db_connection()
                if conn:
                    try:
                        hashed_login_pass = hash_password(login_pass)
                        plain_pass = login_pass.strip()

                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT id, full_name, username, role, class_level 
                                FROM users 
                                WHERE username = %s AND (password = %s OR password = %s)
                            """, (login_user.strip(), hashed_login_pass, plain_pass))
                            user = cur.fetchone()

                            if user:
                                st.session_state.user = {
                                    "id": user[0],
                                    "full_name": user[1],
                                    "username": user[2],
                                    "role": user[3],
                                    "class_level": user[4]
                                }
                                st.rerun()
                            else:
                                st.error("İstifadəçi adı və ya şifrə yanlışdır.")
                    except Exception as e:
                        st.error(f"Giriş xətası: {e}")
                    finally:
                        conn.close()
            else:
                st.warning("Zəhmət olmasa istifadəçi adı və şifrəni daxil edin.")

    with tab2:
        st.subheader("Yeni şagird qeydiyyatı üçün məlumatları daxil edin:")
        new_fullname = st.text_input("Ad Soyad:", key="reg_fullname")
        new_user = st.text_input("İstifadəçi adı (Username):", key="reg_user")
        new_pass = st.text_input("Şifrə təyin edin:", type="password", key="reg_pass")
        new_class = st.selectbox("Sinif seçin:", [3, 4, 5, 6, 7, 8, 9], index=6, key="reg_class")
        new_code = st.text_input("Şagird Kodu (Könüllü):", key="reg_code")

        if st.button("Qeydiyyatı Tamamla", use_container_width=True):
            if new_fullname and new_user and new_pass:
                conn = get_db_connection()
                if conn:
                    try:
                        hashed_new_pass = hash_password(new_pass)
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO users (full_name, username, password, role, student_code, class_level) 
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    new_fullname.strip(),
                                    new_user.strip(),
                                    hashed_new_pass,
                                    "student",
                                    new_code.strip() if new_code.strip() else None,
                                    new_class,
                                ),
                            )
                        conn.commit()
                        st.success("Qeydiyyat uğurla tamamlandı! İndi daxil ola bilərsiniz.")
                    except psycopg2.IntegrityError as err:
                        err_msg = str(err)
                        if "username" in err_msg:
                            st.error("Bu istifadəçi adı artıq götürülüb. Lütfən başqa bir username seçin.")
                        elif "student_code" in err_msg:
                            st.error("Bu Şagird Kodu artıq başqa bir şagirdə təyin edilib.")
                        else:
                            st.error(f"Məlumat təkrarı xətası: {err}")
                    except Exception as e:
                        st.error(f"Qeydiyyat zamanı xəta: {e}")
                    finally:
                        conn.close()
            else:
                st.warning("Zəhmət olmasa tələb olunan xanaları doldurun.")

# ---------------------------------------------------------
# MAIN DASHBOARD (LOGGED IN USER)
# ---------------------------------------------------------
else:
    user = st.session_state.user

    # Sidebar Navigation
    st.sidebar.title(f"👤 {user['full_name']}")
    st.sidebar.info(
        f"Rolu: {user['role'].capitalize()} " + (f"({user['class_level']}-cı Sinif)" if user['class_level'] else ""))

    if st.sidebar.button("🚪 Çıxış Et"):
        st.session_state.user = None
        st.rerun()

    # =========================================================
    # TEACHER DASHBOARD
    # =========================================================
    if user['role'] == 'admin' or user['role'] == 'teacher':
        t_menu = st.sidebar.radio("Müəllim Paneli",
                                  ["📊 Nəticələr və Statistikalar", "📚 Dərs Materialları", "📋 Quizlər və Suallar"])

        # -----------------------------------------------------
        # 1. RESULTS & STATISTICS
        # -----------------------------------------------------
        if t_menu == "📊 Nəticələr və Statistikalar":
            st.header("📊 Şagirdlərin İmtahan Nəticələri")
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT qr.id, u.full_name, qp.title, qr.score, qr.created_at
                            FROM quiz_results qr
                            LEFT JOIN users u ON qr.student_id = u.id
                            LEFT JOIN quiz_packages qp ON qr.package_id = qp.id
                            ORDER BY qr.created_at DESC
                        """)
                        results = cur.fetchall()

                        if results:
                            table_data = []
                            for r in results:
                                table_data.append({
                                    "ID": r[0],
                                    "Şagird": r[1] if r[1] else "Silinmiş İstifadəçi",
                                    "Quiz Paketi": r[2] if r[2] else "General",
                                    "Nəticə (%)": r[3],
                                    "Tarix": str(r[4])[:19] if r[4] else "-"
                                })
                            df = pd.DataFrame(table_data)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.info("Hələ heç bir imtahan nəticəsi yoxdur.")
                except Exception as e:
                    st.error(f"Xəta: {e}")
                finally:
                    conn.close()

        # -----------------------------------------------------
        # 2. DƏRS MATERİALLARI
        # -----------------------------------------------------
        elif t_menu == "📚 Dərs Materialları":
            st.header("📚 Dərs Materiallarının İdarə Edilməsi")

            m_tab1, m_tab2 = st.tabs(["➕ Yeni Material Əlavə Et", "📑 Mövcud Materiallar"])

            with m_tab1:
                with st.form("add_material_form"):
                    m_title = st.text_input("Materialın Adı/Mövzusu:")
                    m_class = st.selectbox("Sinif:", [3, 4, 5, 6, 7, 8, 9])
                    m_content = st.text_area("Material Mətni/Açıqlama:")

                    if st.form_submit_button("Materialı Saxla"):
                        if m_title and m_content:
                            conn = get_db_connection()
                            if conn:
                                try:
                                    with conn.cursor() as cur:
                                        cur.execute(
                                            "INSERT INTO materials (title, class_level, content) VALUES (%s, %s, %s)",
                                            (m_title.strip(), m_class, m_content.strip())
                                        )
                                    conn.commit()
                                    st.success("Material uğurla əlavə edildi!")
                                except Exception as e:
                                    st.error(f"Xəta: {e}")
                                finally:
                                    conn.close()
                        else:
                            st.warning("Mövzu adı və mətni doldurun.")

            with m_tab2:
                conn = get_db_connection()
                if conn:
                    try:
                        with conn.cursor() as cur:
                            cur.execute("SELECT id, title, class_level, content FROM materials ORDER BY id DESC")
                            mats = cur.fetchall()
                            for m in mats:
                                with st.expander(f"📌 {m[1]} ({m[2]}-ci sinif)"):
                                    st.write(m[3])
                    except Exception as e:
                        st.error(f"Materiallar yüklənərkən xəta: {e}")
                    finally:
                        conn.close()

        # -----------------------------------------------------
        # 3. QUİZLƏR VƏ SUALLAR
        # -----------------------------------------------------
        elif t_menu == "📋 Quizlər və Suallar":
            st.header("📋 Quiz Paketi və Sual İdarəetməsi")

            sub_t1, sub_t2 = st.tabs(["📦 Yeni Quiz Paketi Yarat", "➕ Paketə Sual Əlavə Et"])

            with sub_t1:
                with st.form("add_package_form"):
                    p_title = st.text_input("Quiz Paketinin Adı:")
                    p_class = st.selectbox("Sinif:", [3, 4, 5, 6, 7, 8, 9], key="p_class")
                    p_diff = st.selectbox("Çətinlik Səviyyəsi:", ["Asan", "Orta", "Çətin"])
                    p_time = st.number_input("Vaxt Limiti (dəqiqə):", min_value=1, max_value=180, value=20)

                    if st.form_submit_button("Paket Yarat"):
                        if p_title:
                            conn = get_db_connection()
                            if conn:
                                try:
                                    with conn.cursor() as cur:
                                        cur.execute(
                                            "INSERT INTO quiz_packages (title, class_level, difficulty_level, time_limit) VALUES (%s, %s, %s, %s)",
                                            (p_title.strip(), p_class, p_diff, p_time)
                                        )
                                    conn.commit()
                                    st.success("Quiz paketi uğurla yaradıldı!")
                                except Exception as e:
                                    st.error(f"Xəta: {e}")
                                finally:
                                    conn.close()
                        else:
                            st.warning("Paket adını daxil edin.")

            with sub_t2:
                conn = get_db_connection()
                packages = []
                materials_list = []

                if conn:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                "SELECT id, title, class_level, difficulty_level, time_limit FROM quiz_packages ORDER BY id DESC")
                            packages = cur.fetchall()

                            cur.execute("SELECT id, title, class_level FROM materials ORDER BY class_level, title")
                            materials_list = cur.fetchall()
                    except Exception as e:
                        st.error(f"Məlumatlar yüklənərkən xəta: {e}")
                    finally:
                        conn.close()

                if not packages:
                    st.info("Əvvəlcə 'Yeni Quiz Paketi Yarat' bölməsindən paket yaradın.")
                elif not materials_list:
                    st.warning(
                        "Əvvəlcə 'Dərs Materialları' bölməsindən azı bir dərs materialı əlavə edin ki, sualı həmin dərsə bağlaya bilərsiniz.")
                else:
                    pkg_dict = {f"{p[1]} ({p[2]}-ci sinif - {p[3]} - {p[4]} dəq)": p[0] for p in packages}
                    mat_dict = {f"{m[1]} ({m[2]}-ci sinif)": m[0] for m in materials_list}

                    selected_pkg_name = st.selectbox("Sual əlavə olunacaq paketi seçin:", list(pkg_dict.keys()))
                    target_pkg_id = pkg_dict[selected_pkg_name]

                    selected_mat_name = st.selectbox("Sualın aid olduğu dərsi (mövzunu) seçin:", list(mat_dict.keys()))
                    target_lesson_id = mat_dict[selected_mat_name]

                    with st.form("add_question_form_complete", clear_on_submit=True):
                        st.markdown("#### Sual Məlumatları")
                        q_text = st.text_area("Sualın mətni:")
                        opt_a = st.text_input("A variantı:")
                        opt_b = st.text_input("B variantı:")
                        opt_c = st.text_input("C variantı:")
                        opt_d = st.text_input("D variantı:")
                        correct_opt = st.selectbox("Doğru Cavab:", ["A", "B", "C", "D"])

                        if st.form_submit_button("Sualı Əlavə Et"):
                            if q_text and opt_a and opt_b and opt_c and opt_d:
                                conn = get_db_connection()
                                if conn:
                                    try:
                                        with conn.cursor() as cur:
                                            cur.execute("""
                                                INSERT INTO quizzes (quiz_package_id, question_text, option_a, option_b, option_c, option_d, correct_option, lesson_id)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                            """, (
                                                target_pkg_id,
                                                q_text.strip(),
                                                opt_a.strip(),
                                                opt_b.strip(),
                                                opt_c.strip(),
                                                opt_d.strip(),
                                                correct_opt,
                                                target_lesson_id
                                            ))
                                        conn.commit()
                                        st.success("Sual dərslə əlaqələndirilərək uğurla əlavə olundu!")
                                    except Exception as e:
                                        st.error(f"Xəta: {e}")
                                    finally:
                                        conn.close()
                            else:
                                st.warning("Bütün xanaları doldurun.")

    # =========================================================
    # STUDENT DASHBOARD
    # =========================================================
    else:
        s_menu = st.sidebar.radio("Şagird Menyusu",
                                  ["🏠 Əsas Səhifə / Score Board", "📚 Dərs Materialları", "📝 Quizlər və İmtahanlar"])

        # -----------------------------------------------------
        # 1. SCORE BOARD
        # -----------------------------------------------------
        if s_menu == "🏠 Əsas Səhifə / Score Board":
            st.header(f"Xoş gəldin, {user['full_name']}!")
            st.subheader("🏆 Sizin Son İmtahan Nəticələriniz")

            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT qp.title, qr.score, qr.created_at 
                            FROM quiz_results qr
                            LEFT JOIN quiz_packages qp ON qr.package_id = qp.id
                            WHERE qr.student_id = %s
                            ORDER BY qr.created_at DESC
                        """, (user['id'],))
                        my_results = cur.fetchall()

                        if my_results:
                            for r in my_results:
                                st.info(f"📌 **{r[0]}** | Nəticə: **{r[1]}%** | Tarix: {str(r[2])[:19]}")
                        else:
                            st.write("Hələ ki heç bir imtahanda iştirak etməmisiniz.")
                except Exception as e:
                    st.error(f"Xəta: {e}")
                finally:
                    conn.close()

        # -----------------------------------------------------
        # 2. STUDENT MATERIALS
        # -----------------------------------------------------
        elif s_menu == "📚 Dərs Materialları":
            st.header(f"📚 {user['class_level']}-ci Sinif Dərs Materialları")
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id, title, content FROM materials WHERE class_level = %s ORDER BY id DESC",
                                    (user['class_level'],))
                        mats = cur.fetchall()
                        if mats:
                            for m in mats:
                                with st.expander(f"📖 {m[1]}"):
                                    st.write(m[2])
                        else:
                            st.info("Sizin sinfə uyğun material tapılmadı.")
                except Exception as e:
                    st.error(f"Xəta: {e}")
                finally:
                    conn.close()

        # -----------------------------------------------------
        # 3. STUDENT QUIZZES
        # -----------------------------------------------------
        elif s_menu == "📝 Quizlər və İmtahanlar":
            st.header("📝 İmtahanlar və Testlər")

            conn = get_db_connection()
            pkg_list = []
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id, title, difficulty_level, time_limit FROM quiz_packages WHERE class_level = %s ORDER BY id DESC",
                            (user['class_level'],))
                        pkg_list = cur.fetchall()
                except Exception as e:
                    st.error(f"Xəta: {e}")
                finally:
                    conn.close()

            if not pkg_list:
                st.info(f"Hal-hazırda {user['class_level']}-ci sinif üçün aktiv quiz paketi yoxdur.")
            else:
                pkg_options = {f"{p[1]} ({p[2]} - {p[3]} dəq)": p[0] for p in pkg_list}
                selected_pkg_title = st.selectbox("İmtahan paketini seçin:", list(pkg_options.keys()))
                selected_pkg_id = pkg_options[selected_pkg_title]

                # Sualları çəkirik
                conn = get_db_connection()
                questions = []
                if conn:
                    try:
                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option 
                                FROM quizzes 
                                WHERE quiz_package_id = %s
                            """, (selected_pkg_id,))
                            questions = cur.fetchall()
                    except Exception as e:
                        st.error(f"Suallar yüklənərkən xəta: {e}")
                    finally:
                        conn.close()

                if not questions:
                    st.warning("Bu paketdə hələ heç bir sual yoxdur.")
                else:
                    with st.form("take_quiz_form"):
                        user_answers = {}
                        for idx, q in enumerate(questions, 1):
                            st.markdown(f"**Sual {idx}. {q[1]}**")
                            opts = [f"A) {q[2]}", f"B) {q[3]}", f"C) {q[4]}", f"D) {q[5]}"]
                            ans = st.radio(f"Cavabınız ({idx}):", opts, index=None, key=f"q_{q[0]}")
                            if ans:
                                selected_letter = ans[0]  # "A", "B", "C", "D"
                                user_answers[q[0]] = (selected_letter, q[6])
                            st.markdown("---")

                        submitted = st.form_submit_button("İmtahanı Tamamla və Nəticəni Gör")
                        if submitted:
                            score = 0
                            total_q = len(questions)
                            for q_id, (ans, corr) in user_answers.items():
                                if ans == corr:
                                    score += 1

                            final_score = round((score / total_q) * 100, 1) if total_q > 0 else 0

                            # Daxil olan şagirdin məlumatları
                            student_id = user['id']
                            student_name = user['full_name']

                            conn = get_db_connection()
                            if conn:
                                try:
                                    with conn.cursor() as cur:
                                        cur.execute("""
                                            INSERT INTO quiz_results (student_id, student_name, package_id, score) 
                                            VALUES (%s, %s, %s, %s)
                                        """, (student_id, student_name, selected_pkg_id, final_score))
                                    conn.commit()
                                    st.balloons()
                                    st.success(
                                        f"İmtahan başa çatdı! Nəticəniz: {final_score}% ({total_q} sualdan {score} düzgün)")
                                except Exception as e:
                                    st.error(f"Nəticə yadda saxlanılarkən xəta: {e}")
                                finally:
                                    conn.close()