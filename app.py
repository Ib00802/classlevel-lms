import hashlib
import time
import pandas as pd
import psycopg2
import streamlit as st


# ==========================================
# İMTAHAN NƏTİCƏSİ MODAL PƏNCƏRƏSİ
# ==========================================
@st.dialog("📊 İmtahan Nəticəsi və Ətraflı Analiz", width="large")
def show_detailed_results_dialog(
    score_percent,
    total_q,
    correct_cnt,
    wrong_cnt,
    blank_cnt,
    time_spent_str,
    user_answers,
    questions,
):
    st.balloons()

    # 1. Yuxarı Xülasə Paneli
    st.markdown("### 📈 Ümumi Göstəricilər")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Nəticə", f"{score_percent}%")
    m2.metric("⏱️ Vaxt", time_spent_str)
    m3.metric("✅ Düzgün", correct_cnt)
    m4.metric("❌ Səhv", wrong_cnt)
    m5.metric("⚪ Cavabsız", blank_cnt)

    st.write("---")

    # 2. Suallara filtrasiya olunmuş baxış
    st.markdown("### 🔍 Suallara Baxış")
    filter_option = st.radio(
        "Göstəriləcək sualları seçin:",
        [
            "Hamısı",
            "✅ Yalnız Düzgünlər",
            "❌ Yalnız Səhvlər",
            "⚪ Yalnız Cavablandırılmayanlar",
        ],
        horizontal=True,
    )

    st.write("---")

    # 3. Sualların siyahılanması
    for idx, q in enumerate(questions, 1):
        q_id = q[0]
        q_text = q[1]
        opts = {"A": q[2], "B": q[3], "C": q[4], "D": q[5]}
        correct_opt = q[6]

        user_choice = user_answers.get(q_id, (None, None))[0]

        if user_choice is None:
            status = "blank"
        elif user_choice == correct_opt:
            status = "correct"
        else:
            status = "wrong"

        if filter_option == "✅ Yalnız Düzgünlər" and status != "correct":
            continue
        if filter_option == "❌ Yalnız Səhvlər" and status != "wrong":
            continue
        if filter_option == "⚪ Yalnız Cavablandırılmayanlar" and status != "blank":
            continue

        if status == "correct":
            st.success(
                f"**Sual {idx}:** {q_text}  \n✅ **Sizin cavabınız:** {user_choice}) {opts.get(user_choice, '')} *(Doğru)*"
            )
        elif status == "wrong":
            st.error(
                f"**Sual {idx}:** {q_text}  \n❌ **Sizin cavabınız:** {user_choice}) {opts.get(user_choice, '')}  \n🎯 **Doğru cavab:** {correct_opt}) {opts.get(correct_opt, '')}"
            )
        else:
            st.warning(
                f"**Sual {idx}:** {q_text}  \n⚪ **Cavablandırılmayıb**  \n🎯 **Doğru cavab:** {correct_opt}) {opts.get(correct_opt, '')}"
            )

        st.caption("---")

# Səhifə konfiqurasiyası
st.set_page_config(page_title="ClassLevel LMS", page_icon="🎓", layout="wide")


# ==========================================
# BAZA İLƏ BAĞLANTI (Context Manager ilə)
# ==========================================
def get_db_connection():
    """Baza bağlantısını təhlükəsiz şəkildə açır."""
    try:
        if "postgres" in st.secrets:
            return psycopg2.connect(
                host=st.secrets["postgres"]["host"],
                database=st.secrets["postgres"]["database"],
                user=st.secrets["postgres"]["user"],
                password=st.secrets["postgres"]["password"],
                port=st.secrets["postgres"]["port"],
            )
        elif "url" in st.secrets.get("postgres", {}):
            return psycopg2.connect(st.secrets["postgres"]["url"])
        else:
            return psycopg2.connect(
                host=st.secrets["host"],
                database=st.secrets["database"],
                user=st.secrets["user"],
                password=st.secrets["password"],
                port=st.secrets["port"],
            )
    except Exception as e:
        st.error(f"Verilənlər bazasına qoşulma xətası: {e}")
        return None


# Cədvəllərin yalnız bir dəfə yoxlanılması üçün keşləyirik
@st.cache_resource
def init_db():
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            # 1. İstifadəçilər cədvəli
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(255),
                    username VARCHAR(100) UNIQUE,
                    password VARCHAR(100),
                    role VARCHAR(50),
                    student_code VARCHAR(50),
                    class_level INT
                );
            """)

            # 2. Materiallar cədvəli
            cur.execute("""
                CREATE TABLE IF NOT EXISTS materials (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    class_level INT,
                    file_link TEXT,
                    video_link TEXT,
                    content_standard VARCHAR(100),
                    sub_standard VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Quiz paketləri cədvəli
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quiz_packages (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    class_level INT,
                    difficulty_level VARCHAR(50),
                    time_limit INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Suallar cədvəli
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quizzes (
                    id SERIAL PRIMARY KEY,
                    quiz_package_id INT REFERENCES quiz_packages(id) ON DELETE CASCADE,
                    question_text TEXT,
                    option_a TEXT,
                    option_b TEXT,
                    option_c TEXT,
                    option_d TEXT,
                    correct_option VARCHAR(5)
                );
            """)

            # 5. Nəticələr cədvəli
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quiz_results (
                    id SERIAL PRIMARY KEY,
                    student_id INT REFERENCES users(id) ON DELETE CASCADE,
                    package_id INT REFERENCES quiz_packages(id) ON DELETE CASCADE,
                    score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()
    except Exception as e:
        print("DB Init Error:", e)
    finally:
        conn.close()


# Bazanı işə salırıq
init_db()

# Session State tənzimləmələri
if "user" not in st.session_state:
    st.session_state.user = None


def hash_password(password):
    return hashlib.sha256(password.strip().encode()).hexdigest()


# ==========================================
# GİRİŞ VƏ QEYDİYYAT SƏHİFƏSİ
# ==========================================
if st.session_state.user is None:
    st.markdown(
        "<h1 style='text-align: center;'>🎓 ClassLevel LMS</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center;'>Müasir Təhsil və İdarəetmə Portalı</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Sistemə Giriş", "📝 Yeni Qeydiyyat"])

        with tab1:
            username = st.text_input("İstifadəçi adı:", key="login_user")
            password = st.text_input(
                "Şifrə:", type="password", key="login_pass"
            )

            if st.button("Daxil Ol", use_container_width=True):
                if username and password:
                    # Admin girişi
                    admin_pass = st.secrets.get("ADMIN_PASSWORD", "Muellim2026!")
                    if (
                        username.strip() == "admin"
                        and password.strip() == admin_pass
                    ):
                        st.session_state.user = {
                            "id": 0,
                            "full_name": "Sistem Administratoru",
                            "username": "admin",
                            "role": "teacher",
                            "class_level": 0,
                        }
                        st.success("Uğurla daxil oldunuz!")
                        st.rerun()
                    else:
                        conn = get_db_connection()
                        if conn:
                            try:
                                hashed_pass = hash_password(password)
                                # Kohne MD5 hashlerini de yoxlamaq ucun fallback
                                md5_pass = hashlib.md5(
                                    password.strip().encode()
                                ).hexdigest()

                                with conn.cursor() as cur:
                                    cur.execute(
                                        """
                                        SELECT id, full_name, username, role, class_level 
                                        FROM users 
                                        WHERE username = %s AND (password = %s OR password = %s)
                                    """,
                                        (username.strip(), hashed_pass, md5_pass),
                                    )
                                    user_data = cur.fetchone()

                                if user_data:
                                    st.session_state.user = {
                                        "id": user_data[0],
                                        "full_name": user_data[1],
                                        "username": user_data[2],
                                        "role": user_data[3],
                                        "class_level": user_data[4],
                                    }
                                    st.success("Uğurla daxil oldunuz!")
                                    st.rerun()
                                else:
                                    st.error(
                                        "İstifadəçi adı və ya şifrə yanlışdır."
                                    )
                            except Exception as e:
                                st.error(f"Sistem xətası: {e}")
                            finally:
                                conn.close()
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
                    conn = get_db_connection()
                    if conn:
                        try:
                            hashed_new_pass = hash_password(new_pass)
                            with conn.cursor() as cur:
                                cur.execute(
                                    "INSERT INTO users (full_name, username, password, role, student_code, class_level) VALUES (%s, %s, %s, %s, %s, %s)",
                                    (
                                        new_fullname.strip(),
                                        new_user.strip(),
                                        hashed_new_pass,
                                        "student",
                                        new_code.strip(),
                                        new_class,
                                    ),
                                )
                            conn.commit()
                            st.success(
                                "Qeydiyyat uğurla tamamlandı! İndi daxil ola bilərsiniz."
                            )
                        except psycopg2.IntegrityError:
                            st.error(
                                "Bu istifadəçi adı artıq götürülüb. Lütfən başqa bir username seçin."
                            )
                        except Exception as e:
                            st.error(f"Qeydiyyat zamanı xəta: {e}")
                        finally:
                            conn.close()
                else:
                    st.warning("Zəhmət olmasa tələb olunan xanaları doldurun.")

# ==========================================
# İSTİFADƏÇİ SİSTEMƏ DAXİL OLDUQDAN SONRA
# ==========================================
else:
    # --------------------------------------
    # MÜƏLLİM İDARƏETMƏ PANELİ
    # --------------------------------------
    if st.session_state.user["role"] == "teacher":
        st.title("👨‍🏫 Müəllim İdarəetmə Paneli")

        st.sidebar.markdown(f"### 👨‍🏫 {st.session_state.user['full_name']}")
        st.sidebar.caption("Status: Müəllim / Admin")

        if st.sidebar.button("🚪 Çıxış Et", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        m_t1, m_t2, m_t3 = st.tabs(
            [
                "👥 Şagirdlər",
                "📚 Materiallar (Standart və Linklər)",
                "📝 Quiz Paketi və Suallar",
            ]
        )

        with m_t1:
            st.subheader("👥 Qeydiyyatdan Keçmiş Şagirdlər")
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id, full_name, username, student_code, class_level FROM users WHERE role = 'student' ORDER BY class_level, full_name"
                        )
                        students_data = cur.fetchall()

                    if students_data:
                        df_students = pd.DataFrame(
                            students_data,
                            columns=[
                                "ID",
                                "Ad Soyad",
                                "İstifadəçi Adı",
                                "Şagird Kodu",
                                "Sinif",
                            ],
                        )
                        st.dataframe(
                            df_students,
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info(
                            "Hələ ki sistemdə qeydiyyatdan keçmiş şagird yoxdur."
                        )
                except Exception as e:
                    st.error(f"Şagird siyahısı yüklənərkən xəta: {e}")
                finally:
                    conn.close()

        with m_t2:
            st.subheader("📚 Dərs Materiallarının Yerləşdirilməsi")

            with st.form("add_material_advanced_form", clear_on_submit=True):
                st.markdown("### ➕ Yeni Material Əlavə Et")
                mat_title = st.text_input("Mövzunun Adı:")
                mat_class = st.selectbox(
                    "Sinif:", list(range(1, 12)), index=8, key="mat_cl_full"
                )
                mat_file = st.text_input("PDF / Fayl Linki:")
                mat_video = st.text_input("Video Dərs Linki:")
                mat_content_std = st.text_input(
                    "Məzmun Standartı (məs: 2.1.1.):"
                )
                mat_sub_std = st.text_input("Alt Standart (məs: 2.1.3.):")

                if st.form_submit_button("Materialı Bazaya Yüklə"):
                    if mat_title:
                        conn = get_db_connection()
                        if conn:
                            try:
                                with conn.cursor() as cur:
                                    cur.execute(
                                        """
                                        INSERT INTO materials (title, class_level, file_link, video_link, content_standard, sub_standard)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """,
                                        (
                                            mat_title.strip(),
                                            int(mat_class),
                                            mat_file.strip(),
                                            mat_video.strip(),
                                            mat_content_std.strip(),
                                            mat_sub_std.strip(),
                                        ),
                                    )
                                conn.commit()
                                st.success("Material uğurla əlavə olundu!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Xəta: {e}")
                            finally:
                                conn.close()
                    else:
                        st.warning("Mövzu adını daxil edin.")

            st.write("---")
            st.markdown("### 📋 Yüklənmiş Materialların Siyahısı")
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id, title, class_level, file_link, video_link, content_standard, sub_standard FROM materials ORDER BY class_level, id DESC"
                        )
                        mats = cur.fetchall()

                    if mats:
                        df_mats = pd.DataFrame(
                            mats,
                            columns=[
                                "ID",
                                "Mövzu",
                                "Sinif",
                                "Fayl Linki",
                                "Video Link",
                                "Məzmun Standartı",
                                "Alt Standart",
                            ],
                        )
                        st.dataframe(
                            df_mats, use_container_width=True, hide_index=True
                        )
                    else:
                        st.info("Hələ ki heç bir material əlavə olunmayıb.")
                except Exception as e:
                    st.error(f"Xəta: {e}")
                finally:
                    conn.close()

        with m_t3:
            st.subheader("📝 Quiz Paketi və Sualların İdarə Edilməsi")
            sub_t1, sub_t2 = st.tabs(
                ["📦 Yeni Quiz Paketi Yarat", "➕ Paketə Sual Əlavə Et"]
            )

            with sub_t1:
                with st.form("create_quiz_pkg_complete"):
                    pkg_title = st.text_input("Quiz Paketinin Adı:")
                    pkg_class = st.selectbox(
                        "Aid Olduğu Sinif:",
                        list(range(1, 12)),
                        index=8,
                        key="pkg_cl_full",
                    )
                    pkg_difficulty = st.selectbox(
                        "Çətinlik Səviyyəsi:", ["Asan", "Orta", "Çətin"]
                    )
                    pkg_time = st.number_input(
                        "İşləmə Müddəti (dəqiqə ilə):",
                        min_value=1,
                        max_value=180,
                        value=30,
                    )

                    if st.form_submit_button("Quiz Paketini Yarat"):
                        if pkg_title:
                            conn = get_db_connection()
                            if conn:
                                try:
                                    with conn.cursor() as cur:
                                        cur.execute(
                                            """
                                            INSERT INTO quiz_packages (title, class_level, difficulty_level, time_limit)
                                            VALUES (%s, %s, %s, %s)
                                        """,
                                            (
                                                pkg_title.strip(),
                                                int(pkg_class),
                                                pkg_difficulty,
                                                int(pkg_time),
                                            ),
                                        )
                                    conn.commit()
                                    st.success(
                                        "Quiz paketi uğurla yaradıldı!"
                                    )
                                except Exception as e:
                                    st.error(f"Xəta: {e}")
                                finally:
                                    conn.close()
                        else:
                            st.warning("Quiz paketinin adını daxil edin.")

            with sub_t2:
                conn = get_db_connection()
                packages = []
                materials_list = []

                if conn:
                    try:
                        with conn.cursor() as cur:
                            # Quiz paketlərini çəkirik
                            cur.execute(
                                "SELECT id, title, class_level, difficulty_level, time_limit FROM quiz_packages ORDER BY id DESC")
                            packages = cur.fetchall()

                            # Mövcud dərs materiallarını (lessons) çəkirik
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
                        "Əvvəlcə 'Materiallar' bölməsindən azı bir dərs materialı əlavə edin ki, sualı həmin dərsə bağlaya bilərsiniz.")
                else:
                    pkg_dict = {f"{p[1]} ({p[2]}-ci sinif - {p[3]} - {p[4]} dəq)": p[0] for p in packages}
                    mat_dict = {f"{m[1]} ({m[2]}-ci sinif)": m[0] for m in materials_list}

                    selected_pkg_name = st.selectbox("Sual əlavə olunacaq paketi seçin:", list(pkg_dict.keys()))
                    target_pkg_id = pkg_dict[selected_pkg_name]

                    # Sualın aid olacağı dərsi/materialı seçirik
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
                                            # lesson_id artıq məcburi olaraq INSERT edilir!
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
                                                target_lesson_id  # Mövzunun ID-si göndərilir
                                            ))
                                        conn.commit()
                                        st.success("Sual dərslə əlaqələndirilərək uğurla əlavə olundu!")
                                    except Exception as e:
                                        st.error(f"Xəta: {e}")
                                    finally:
                                        conn.close()
                            else:
                                st.warning("Bütün xanaları doldurun.")

    # --------------------------------------
    # ŞAGİRD PANELİ
    # --------------------------------------
    elif st.session_state.user["role"] == "student":
        student_class = st.session_state.user.get("class_level", 9)
        student_id = st.session_state.user["id"]

        st.sidebar.markdown(f"### 🎓 {st.session_state.user['full_name']}")
        st.sidebar.info(f"📌 {student_class}-cı Sinif Şagirdi")

        s_menu = st.sidebar.radio(
            "Menyu",
            [
                "🏠 Əsas Səhifə / Score Board",
                "📚 Dərs Materialları",
                "📝 Quizlər və İmtahanlar",
            ],
            label_visibility="collapsed",
        )

        st.sidebar.write("---")
        if st.sidebar.button("🚪 Çıxış Et", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        if s_menu == "🏠 Əsas Səhifə / Score Board":
            st.header("🏠 Xoş Gəldiniz!")
            st.write(f"Salam, **{st.session_state.user['full_name']}**!")

            st.write("---")
            st.subheader("🏆 Liderlər Lövhəsi (Score Board)")
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT u.full_name, u.class_level, COALESCE(SUM(r.score), 0) as total_score, COUNT(r.id) as total_quizzes
                            FROM users u
                            LEFT JOIN quiz_results r ON u.id = r.student_id
                            WHERE u.role = 'student'
                            GROUP BY u.id, u.full_name, u.class_level
                            ORDER BY total_score DESC, total_quizzes DESC
                        """)
                        scores = cur.fetchall()

                    if scores:
                        df_scores = pd.DataFrame(
                            scores,
                            columns=[
                                "Şagird",
                                "Sinif",
                                "Ümumi Bal",
                                "İşlənmiş Quiz Sayı",
                            ],
                        )
                        st.dataframe(
                            df_scores,
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info("Hələ ki heç bir nəticə qeydə alınmayıb.")
                except Exception as e:
                    st.info("Liderlər lövhəsi yenilənir.")
                finally:
                    conn.close()

        elif s_menu == "📚 Dərs Materialları":
            st.header("📚 Dərs Materialları")
            st.write(
                f"**{student_class}-cı sinif** üçün əlçatan dərs materialları:"
            )

            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT title, file_link, video_link, content_standard, sub_standard, created_at 
                            FROM materials 
                            WHERE class_level = %s 
                            ORDER BY id DESC
                        """,
                            (student_class,),
                        )
                        materials = cur.fetchall()

                    if materials:
                        for (
                            mat_title,
                            mat_file,
                            mat_video,
                            mat_cs,
                            mat_ss,
                            mat_date,
                        ) in materials:
                            with st.container():
                                st.markdown(f"### 📖 Mövzu: {mat_title}")
                                if mat_cs or mat_ss:
                                    st.caption(
                                        f"📌 Məzmun Standartı: {mat_cs} | Alt Standart: {mat_ss}"
                                    )

                                col_f, col_v = st.columns(2)
                                with col_f:
                                    if mat_file:
                                        st.markdown(
                                            f"[📥 PDF / Fayl Materialı]({mat_file})"
                                        )
                                with col_v:
                                    if mat_video:
                                        st.markdown(
                                            f"[📺 Video Dərsə Bax]({mat_video})"
                                        )

                                st.caption(f"Yüklənmə tarixi: {mat_date}")
                                st.write("---")
                    else:
                        st.info(
                            f"{student_class}-cı sinif üçün hələ ki dərs materialı əlavə olunmayıb."
                        )
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
                        cur.execute("SELECT id, title, difficulty_level, time_limit FROM quiz_packages WHERE class_level = %s ORDER BY id DESC",
                                    (st.session_state.user['class_level'],))

                        pkg_list = cur.fetchall()
                except Exception as e:
                    st.error(f"Xəta: {e}")
                finally:
                    conn.close()
            if not pkg_list:
                st.info(f"Hal-hazırda {st.session_state.user['class_level']}-ci sinif üçün aktiv quiz paketi yoxdur.")
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
                    if "start_time" not in st.session_state:
                        st.session_state.start_time = time.time()
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
                            # 1. Vaxt fərqini hesablayırıq
                            end_time = time.time()
                            elapsed_seconds = int(
                                end_time
                                - st.session_state.get("start_time", end_time)
                            )
                            # Növbəti imtahan üçün taymeri sıfırlayırıq
                            if "start_time" in st.session_state:
                                del st.session_state["start_time"]

                            minutes = elapsed_seconds // 60
                            seconds = elapsed_seconds % 60
                            time_spent_str = f"{minutes} dəq {seconds} san"

                            total_q = len(questions)
                            correct_cnt = 0
                            wrong_cnt = 0
                            blank_cnt = 0

                            # 2. Cavabların təhlili və sayılması
                            for q in questions:
                                q_id = q[0]
                                correct_opt = q[6]
                                user_choice = user_answers.get(
                                    q_id, (None, None)
                                )[0]

                                if user_choice is None:
                                    blank_cnt += 1
                                elif user_choice == correct_opt:
                                    correct_cnt += 1
                                else:
                                    wrong_cnt += 1

                            percentage_score = (
                                round((correct_cnt / total_q) * 100, 1)
                                if total_q > 0
                                else 0
                            )

                            # 3. Məlumatların bazaya saxlanılması
                            student_id = st.session_state.user["id"]
                            student_name = st.session_state.user["full_name"]
                            student_class = st.session_state.user["class_level"]
                            quiz_title = selected_pkg_title

                            conn = get_db_connection()
                            if conn:
                                try:
                                    with conn.cursor() as cur:
                                        cur.execute(
                                            """
                                            INSERT INTO quiz_results (
                                                student_id, 
                                                student_name, 
                                                class_level, 
                                                quiz_title, 
                                                score, 
                                                total_questions, 
                                                percentage, 
                                                package_id
                                            ) 
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                        """,
                                            (
                                                student_id,
                                                student_name,
                                                student_class,
                                                quiz_title,
                                                correct_cnt,
                                                total_q,
                                                percentage_score,
                                                selected_pkg_id,
                                            ),
                                        )
                                    conn.commit()
                                except Exception as e:
                                    st.error(
                                        f"Nəticə yadda saxlanılarkən xəta: {e}"
                                    )
                                finally:
                                    conn.close()

                            # 4. Ətraflı analiz üçün modal pəncərəni açırıq
                            show_detailed_results_dialog(
                                percentage_score,
                                total_q,
                                correct_cnt,
                                wrong_cnt,
                                blank_cnt,
                                time_spent_str,
                                user_answers,
                                questions,
                            )