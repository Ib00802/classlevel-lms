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
): pass

# ==========================================
# QUİZ LİMİTİNİ YOXLAYAN FUNKSİYA (3 GÜN)
# ==========================================
from datetime import datetime, timezone
def check_quiz_lock_status(student_id, package_id):
    conn = get_db_connection()
    is_locked = False
    time_left_str = ""
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT created_at FROM quiz_results WHERE student_id = %s AND package_id = %s",
                    (student_id, package_id),
                )
                result = cur.fetchone()
                if result and result[0]:
                    last_attempt = result[0]

                    # Əgər bazadan gələn dəyər string-dirsə datetime-a çeviririk
                    if isinstance(last_attempt, str):
                        last_attempt = datetime.fromisoformat(
                            last_attempt.replace("Z", "+00:00")
                        )

                    # Timezone fərqini neytrallaşdırırıq (Naive UTC edirik)
                    if (
                        hasattr(last_attempt, "tzinfo")
                        and last_attempt.tzinfo is not None
                    ):
                        last_attempt = last_attempt.astimezone(
                            timezone.utc
                        ).replace(tzinfo=None)

                    # Hazırkı vaxtı da Naive UTC götürürük
                    cur.execute("SELECT NOW() AT TIME ZONE 'UTC'")
                    now = cur.fetchone()[0]
                    if hasattr(now, "tzinfo") and now.tzinfo is not None:
                        now = now.replace(tzinfo=None)

                    time_diff = now - last_attempt
                    total_seconds_passed = time_diff.total_seconds()
                    three_days_in_seconds = 3 * 24 * 3600

                    if total_seconds_passed < three_days_in_seconds:
                        is_locked = True
                        rem_sec = three_days_in_seconds - total_seconds_passed
                        hours = int(rem_sec // 3600)
                        minutes = int((rem_sec % 3600) // 60)
                        if hours >= 24:
                            time_left_str = f"{hours // 24} gün {hours % 24} saat {minutes} dəq"
                        else:
                            time_left_str = f"{hours} saat {minutes} dəq"
        except Exception as e:
            st.error(f"Limit yoxlanarkən xəta: {e}")
        finally:
            conn.close()
    return is_locked, time_left_str

    def save_quiz_result(
            student_id,
            student_name,
            student_class,
            quiz_title,
            correct_cnt,
            total_q,
            percentage_score,
            selected_pkg_id,
    ):
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    # Əvvəl bu tələbənin bu paket üzrə nəticəsinin olub-olmadığını yoxlayırıq
                    cur.execute(
                        """
                        SELECT id FROM quiz_results 
                        WHERE student_id = %s AND package_id = %s
                        """,
                        (student_id, selected_pkg_id),
                    )
                    existing_result = cur.fetchone()

                    if existing_result:
                        # Nəticə varsa, UPDATE edirik
                        cur.execute(
                            """
                            UPDATE quiz_results 
                            SET score = %s,
                                total_questions = %s,
                                percentage = %s,
                                quiz_title = %s,
                                created_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            """,
                            (
                                correct_cnt,
                                total_q,
                                percentage_score,
                                quiz_title,
                                existing_result[0],
                            ),
                        )
                    else:
                        # Nəticə yoxdursa, INSERT edirik
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
                                package_id,
                                created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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
                return True
            except Exception as e:
                st.error(f"Nəticə bazaya yazılarkən xəta: {e}")
                return False
            finally:
                conn.close()
        return False

    # Nəticəyə uyğun Emosiya və Animasiya
    if score_percent >= 90:
        st.balloons()  # Yalnız 90-100% üçün konfeti/şar animasiyası
        st.success(
            f"🏆 **MÜKƏMMƏL! Siz Çempionsunuz!**  \nNəticəniz: **{score_percent}%**"
        )
    elif score_percent >= 70:
        st.success(
            f"🥳 **Əla Nəticə! Çox yaxşı iş çıxardınız!**  \nNəticəniz: **{score_percent}%**"
        )
    elif score_percent >= 50:
        st.info(
            f"😐 **Orta Nəticə.** Bir az da təkrar etsəniz daha yaxşı olar!  \nNəticəniz: **{score_percent}%**"
        )
    else:
        st.error(
            f"💔 **Məyus Olmayın!** Mövzunu yaxşıca öyrənib yenidən cəhd edin.  \nNəticəniz: **{score_percent}%**"
        )

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
def render_add_question_form(selected_package_id, selected_package_title=""):
    """
    Sual daxil etmə formasını və bazaya yazma məntiqini tək bir yerdən idarə edir.
    """
    st.markdown(f"### 📝 **{selected_package_title}** üçün sual əlavə edin")

    with st.form(key=f"add_question_form_{selected_package_id}"):
        q_text = st.text_area("Sualın mətni:")
        opt_a = st.text_input("A variantı:")
        opt_b = st.text_input("B variantı:")
        opt_c = st.text_input("C variantı:")
        opt_d = st.text_input("D variantı:")
        correct_opt = st.selectbox("Düzgün cavab:", ["A", "B", "C", "D"])
        q_solution = st.text_area(
            "Sualın həll yolu (izahı):",
            help="İmtahan bitdikdə şagird bu izahı görəcək.",
        )

        submit_q = st.form_submit_button("Sualı Yadda Saxla")

        if submit_q:
            if not q_text or not opt_a or not opt_b or not opt_c or not opt_d:
                st.warning("Zəhmət olmasa, sual mətni və bütün variantları doldurun!")
            else:
                conn = get_db_connection()
                if conn:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO quizzes (
                                    lesson_id, quiz_title, question_text, 
                                    option_a, option_b, option_c, option_d, 
                                    correct_option, solution
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    selected_package_id,
                                    selected_package_title,
                                    q_text,
                                    opt_a,
                                    opt_b,
                                    opt_c,
                                    opt_d,
                                    correct_opt,
                                    q_solution,
                                ),
                            )
                        conn.commit()
                        st.success("Sual uğurla paketə əlavə olundu!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sual əlavə edilərkən xəta: {e}")
                    finally:
                        conn.close()

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
def save_quiz_result(student_id, student_name, student_class, quiz_title, correct_cnt, total_q, percentage_score,
                     selected_pkg_id):
    pass


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
        # Müəllim paneli üçün tab-lar
        tab_add, tab_manage, tab_scores = st.tabs(
            ["➕ Yeni Sual Əlavə Et", "⚙️ Sualları İdarə Et", "📊 Şagird Nəticələri"]
        )

        with tab_manage:
            st.subheader("Mövcud Sualların Redaktəsi və Silinməsi")
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id, question_text, quiz_title FROM quizzes ORDER BY id DESC"
                        )
                        all_q = cur.fetchall()

                    if all_q:
                        q_dict = {f"ID {q[0]}: {q[1][:40]}... ({q[2]})": q[0] for q in all_q}
                        selected_q_label = st.selectbox("İdarə ediləcək sualı seçin:", list(q_dict.keys()))
                        selected_q_id = q_dict[selected_q_label]

                        col_del, col_edit = st.columns([1, 4])
                        with col_del:
                            if st.button("🗑️ Sualı Sil", type="primary"):
                                with conn.cursor() as cur:
                                    cur.execute("DELETE FROM quizzes WHERE id = %s", (selected_q_id,))
                                conn.commit()
                                st.success("Sual bazadan silindi!")
                                st.rerun()
                except Exception as e:
                    st.error(f"Xəta baş verdi: {e}")
                finally:
                    conn.close()

        with tab_scores:
            st.subheader("🏆 Şagirdlərin İmtahan Nəticələri")
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        # r.user_id əvəzinə r.student_id istifadə edirik
                        cur.execute("""
                            SELECT 
                                r.id, 
                                r.student_name, 
                                r.class_level, 
                                r.quiz_title, 
                                r.score, 
                                r.total_questions, 
                                r.percentage, 
                                r.created_at 
                            FROM quiz_results r
                            ORDER BY r.created_at DESC
                        """)
                        results = cur.fetchall()

                        if results:
                            # Cədvəl sütunlarını səliqəli göstərmək üçün
                            import pandas as pd

                            df = pd.DataFrame(
                                results,
                                columns=[
                                    "ID",
                                    "Şagird",
                                    "Sinif",
                                    "İmtahan",
                                    "Düzgün",
                                    "Ümumi Sual",
                                    "Nəticə (%)",
                                    "Tarix",
                                ],
                            )
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.info("Hələ heç bir imtahan nəticəsi yoxdur.")
                except Exception as e:
                    st.error(f"Nəticələr yüklənərkən xəta: {e}")
                finally:
                    conn.close()

        with m_t3:
            st.subheader("📝 Quiz Paketi və Sualların İdarə Edilməsi")
            tab1, tab2 = st.tabs(["📦 Yeni Quiz Paketi Yarat", "➕ Paketə Sual Əlavə Et"])

            # --- TAB 1: Yalnız Paket Yaratmaq Üçün ---
            with tab1:
                st.subheader("Yeni Quiz Paketi Yarat")

                pkg_title = st.text_input("Quiz Paketinin Adı:")
                pkg_class = st.selectbox("Aid Olduğu Sinif:", [5, 6, 7, 8, 9, 10, 11])
                pkg_diff = st.selectbox("Çətinlik Səviyyəsi:", ["Asan", "Orta", "Çətin"])
                pkg_duration = st.number_input(
                    "İşləmə Müddəti (dəqiqə ilə):", min_value=1, value=15
                )

                if st.button("Quiz Paketini Yarat"):
                    if not pkg_title:
                        st.warning("Lütfən paket adını daxil edin!")
                    else:
                        conn = get_db_connection()
                        if conn:
                            try:
                                with conn.cursor() as cur:
                                    cur.execute(
                                        """
                                        INSERT INTO quiz_packages (title, class_level, difficulty, duration_minutes) 
                                        VALUES (%s, %s, %s, %s)
                                        """,
                                        (pkg_title, pkg_class, pkg_diff, pkg_duration),
                                    )
                                conn.commit()
                                st.success(
                                    "Quiz paketi uğurla yaradıldı! İndi 'Paketə Sual Əlavə Et' tabından sualları daxil edə bilərsiniz.")
                            except Exception as e:
                                st.error(f"Paket yaradılarkən xəta: {e}")
                            finally:
                                conn.close()

            # --- TAB 2: Yalnız Mövcud Paketlərə Sual Əlavə Etmək Üçün ---
            with tab2:
                st.subheader("Mövcud Paketə Sual Əlavə Et")

                conn = get_db_connection()
                if conn:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                "SELECT id, title, class_level FROM quiz_packages ORDER BY id DESC"
                            )
                            packages = cur.fetchall()

                        if packages:
                            pkg_options = {
                                f"{p[1]} ({p[2]}-ci sinif)": (p[0], p[1]) for p in packages
                            }
                            selected_pkg_label = st.selectbox(
                                "Sualların əlavə ediləcəyi paketi seçin:",
                                list(pkg_options.keys()),
                                key="select_pkg_for_add_question_unique",
                            )

                            selected_pkg_id, selected_pkg_title = pkg_options[selected_pkg_label]

                            # Yuxarıda yaratdığımız təknik funksiyanı çağırırıq:
                            render_add_question_form(selected_pkg_id, selected_pkg_title)
                        else:
                            st.info(
                                "Hələ heç bir paket yaradılmayıb. Əvvəlcə 'Yeni Quiz Paketi Yarat' bölməsindən paket yaradın."
                            )
                    except Exception as e:
                        st.error(f"Paketlər yüklənərkən xəta: {e}")
                    finally:
                        conn.close()

            # 1. Müəllim panelində mövcud paketləri bazadan çəkirik
            conn = get_db_connection()
            pkg_list = []
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id, title, class_level FROM quiz_packages ORDER BY id DESC"
                        )
                        pkg_list = cur.fetchall()
                except Exception as e:
                    st.error(f"Paketlər yüklənərkən xəta: {e}")
                finally:
                    conn.close()

            if not pkg_list:
                st.warning("Hələ heç bir quiz paketi yaradılmayıb. Əvvəlcə paket yaradın.")
            else:
                # 2. Seçim qutusunu qururuq
                pkg_options = {f"{p[1]} ({p[2]}-ci sinif)": p[0] for p in pkg_list}
                pkg_titles_map = {p[0]: p[1] for p in pkg_list}

                # Dəyişənlər burada təyin olunur (Unresolved reference xətası aradan qalxır)
                selected_pkg_label = st.selectbox(
                    "Sualların əlavə ediləcəyi paketi seçin:", list(pkg_options.keys())
                )
                selected_pkg_id = pkg_options[selected_pkg_label]
                selected_pkg_title = pkg_titles_map[selected_pkg_id]

                # 3. Sual daxil etmə formu
                with st.form("add_question_form"):
                    q_solution=st.text_area("Sualın həll yolu (izahı):", help="Şagird testi bitirdikdən sonra bu izahı görəcək. ",)
                    q_text = st.text_area("Sualın mətni:")
                    opt_a = st.text_input("A varianti:")
                    opt_b = st.text_input("B varianti:")
                    opt_c = st.text_input("C varianti:")
                    opt_d = st.text_input("D varianti:")
                    correct_opt = st.selectbox("Düzgün cavab:", ["A", "B", "C", "D"])

                    submitted = st.form_submit_button("Sualı Əlavə Et")

                    if submitted:
                        if not q_text or not opt_a or not opt_b or not opt_c or not opt_d:
                            st.error("Lütfən bütün xanaları doldurun!")
                        else:
                            conn = get_db_connection()
                            if conn:
                                try:
                                    with conn.cursor() as cur:
                                        cur.execute(
                                            """
                                            INSERT INTO quizzes (
                                                lesson_id, 
                                                quiz_title, 
                                                question_text, 
                                                option_a, 
                                                option_b, 
                                                option_c, 
                                                option_d, 
                                                correct_option
                                                solution
                                            ) 
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                            """,
                                            (
                                                selected_pkg_id,
                                                selected_pkg_title,
                                                q_text,
                                                opt_a,
                                                opt_b,
                                                opt_c,
                                                opt_d,
                                                correct_opt,
                                                q_solution, # Həll yolu dəyəri daxil edilir
                                            ),
                                        )
                                    conn.commit()
                                    st.success("Sual uğurla əlavə olundu!")
                                except Exception as e:
                                    st.error(f"Sual əlavə olunarkən xəta: {e}")
                                finally:
                                    conn.close()
                            else:
                                st.warning("Bütün xanaları doldurun.")

    # --------------------------------------
    # ŞAGİRD PANELİ
    # --------------------------------------
    elif st.session_state.user["role"] == "student":
        # 1. Dəyişənləri təyin edirik (Xətaların qarşısını almaq üçün)
        student_class = st.session_state.user.get("class_level", 9)
        student_id = st.session_state.user["id"]

        # 2. Sol menyu (Sidebar)
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

        # 3. Əsas Səhifə və Şəxsi Nəticələr (Konfidential)
        if s_menu == "🏠 Əsas Səhifə / Score Board":
            st.header("🏠 Xoş Gəldiniz!")
            st.write(f"Salam, **{st.session_state.user['full_name']}**!")

            st.write("---")
            st.subheader("📊 Mənim Son İmtahan Nəticələrim")

            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        # Sadəcə daxil olan şagirdin nəticələrini çəkirik
                        cur.execute(
                            """
                            SELECT quiz_title, score, total_questions, percentage, created_at 
                            FROM quiz_results 
                            WHERE student_id = %s 
                            ORDER BY created_at DESC
                        """,
                            (student_id,),
                        )

                        user_results = cur.fetchall()

                    if user_results:
                        df = pd.DataFrame(
                            user_results,
                            columns=[
                                "Quiz Adı",
                                "Düzgün Sayı",
                                "Ümumi Sual",
                                "Nəticə (%)",
                                "Tarix",
                            ],
                        )
                        df["Tarix"] = pd.to_datetime(df["Tarix"]).dt.strftime(
                            "%Y-%m-%d %H:%M"
                        )
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Hələ ki heç bir imtahan nəticəniz yoxdur.")
                except Exception as e:
                    st.error(f"Nəticələr yüklənərkən xəta: {e}")
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

            student_id = st.session_state.user["id"]
            student_class = st.session_state.user.get("class_level", 9)

            conn = get_db_connection()
            pkg_list = []
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id, title, difficulty_level, time_limit FROM quiz_packages WHERE class_level = %s ORDER BY id DESC",
                            (student_class,),
                        )
                        pkg_list = cur.fetchall()
                except Exception as e:
                    st.error(f"Paketlər yüklənərkən xəta: {e}")
                finally:
                    conn.close()

            if not pkg_list:
                st.info(
                    f"Hal-hazırda {student_class}-ci sinif üçün aktiv quiz paketi yoxdur."
                )
            else:
                pkg_options = {
                    f"{p[1]} ({p[2]} - {p[3]} dəq)": p[0] for p in pkg_list
                }
                selected_pkg_title = st.selectbox(
                    "İmtahan paketini seçin:", list(pkg_options.keys())
                )
                selected_pkg_id = pkg_options[selected_pkg_title]

                # ⏳ LIMIT YOXLAMASI
                is_locked, time_left = check_quiz_lock_status(
                    student_id, selected_pkg_id
                )

                if is_locked:
                    # 🔒 İmtahan kilitlidirsə YALNIZ xəbərdarlıqlar çıxır, aşağıdakı kodlar İCRA OLUNMUR
                    st.warning(
                        f"⏳ Bu imtahanı yaxınlarda tamamlamısınız. 3 günlük limit qaydasına əsasən təkrar cəhd üçün **{time_left}** gözləməlisiniz."
                    )
                    st.info(
                        "💡 İmtahan nəticələrinizə və səhvlərinizə 'Əsas Səhifə / Score Board' bölməsindən baxa bilərsiniz."
                    )

                else:
                    # 🔓 İmtahan açıq olduqda suallar çəkilir və sizin Taymer + Analiz kodunuz işləyir
                    conn = get_db_connection()
                    questions = []
                    if conn:
                        try:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option , solution"
                                    "FROM quizzes WHERE lesson_id = %s ORDER BY id ASC",
                                    (selected_pkg_id,),
                                )
                                questions = cur.fetchall()
                        except Exception as e:
                            st.error(f"Suallar yüklənərkən xəta: {e}")
                        finally:
                            conn.close()

                    # SİZİN SEVDİYİNİZ VƏ İSTƏDİYİNİZ BÜTÜN FUNKSİONAL KOD BURADA:
                    if not questions:
                        st.warning("Bu paketdə hələ ki heç bir sual yoxdur.")
                    else:
                        if "start_time" not in st.session_state:
                            st.session_state.start_time = time.time()

                        with st.form("take_quiz_form"):
                            user_answers = {}
                            for idx, q in enumerate(questions, 1):
                                st.markdown(f"**Sual {idx}. {q[1]}**")
                                opts = [
                                    f"A) {q[2]}",
                                    f"B) {q[3]}",
                                    f"C) {q[4]}",
                                    f"D) {q[5]}",
                                ]
                                ans = st.radio(
                                    f"Cavabınız ({idx}):",
                                    opts,
                                    index=None,
                                    key=f"q_{q[0]}",
                                )
                                if ans:
                                    selected_letter = ans[0]  # "A", "B", "C", "D"
                                    user_answers[q[0]] = (selected_letter, q[6])
                                st.markdown("---")

                            submitted = st.form_submit_button(
                                "İmtahanı Tamamla və Nəticəni Gör"
                            )

                            if submitted:
                                # 1. Vaxt fərqini hesablayırıq
                                end_time = time.time()
                                elapsed_seconds = int(
                                    end_time
                                    - st.session_state.get("start_time", end_time)
                                )

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
                                    else 0.0
                                )

                                # 3. Məlumatların toplanması
                                student_id = st.session_state.user["id"]
                                student_name = st.session_state.user["full_name"]
                                student_class = st.session_state.user["class_level"]
                                quiz_title = selected_pkg_title

                                # 4. Bazaya Saxlanma Hissəsi
                                conn = get_db_connection()
                                if conn:
                                    try:
                                        with conn.cursor() as cur:
                                            # A) Köhnə nəticəni silirik
                                            cur.execute(
                                                """
                                                DELETE FROM quiz_results 
                                                WHERE student_id = %s AND package_id = %s
                                            """,
                                                (student_id, selected_pkg_id),
                                            )

                                            # B) Yeni nəticəni yazırıq
                                            save_quiz_result(
                                                student_id,
                                                student_name,
                                                student_class,
                                                quiz_title,
                                                correct_cnt,
                                                total_q,
                                                percentage_score,
                                                selected_pkg_id,
                                            )
                                    except Exception as e:
                                        st.error(
                                            f"Nəticə yadda saxlanılarkən xəta: {e}"
                                        )
                                    finally:
                                        conn.close()


                                @st.dialog("📊 İmtahan Nəticəsi və Ətraflı Analiz", width="large")
                                def show_detailed_results_dialog(
                                        percentage_score,
                                        total_q,
                                        correct_cnt,
                                        wrong_cnt,
                                        blank_cnt,
                                        time_spent_str,
                                        user_answers,
                                        questions,
                                ):
                                    # 1. Ümumi Statistika Metrikləri
                                    st.subheader(f"Ümumi Nəticəniz: **{percentage_score}%**")

                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("Sual Sayı", total_q)
                                    col2.metric("Düzgün", correct_cnt, delta=f"{correct_cnt} düz")
                                    col3.metric("Səhv", wrong_cnt, delta=f"-{wrong_cnt} səhv", delta_color="inverse")
                                    col4.metric("Boş", blank_cnt)

                                    st.caption(f"⏱️ **İstifadə olunan vaxt:** {time_spent_str}")
                                    st.divider()

                                    # 2. Sualların Ətraflı Analizi
                                    st.subheader("🔍 Suallar və Cavablarınız")

                                    for idx, q in enumerate(questions, 1):
                                        # Bazadakı sütun sırasına uyğun: id, question_text, option_a, option_b, option_c, option_d, correct_option, solution
                                        q_id = q[0]
                                        q_text = q[1]
                                        opts = {"A": q[2], "B": q[3], "C": q[4], "D": q[5]}
                                        correct_opt = q[6]

                                        # Əgər bazada solution (həll yolu) sütunu varsa (indeks 7), onu götürürük
                                        q_solution = q[7] if len(q) > 7 and q[
                                            7] else "Bu sual üçün daxil edilmiş xüsusi həll yolu yoxdur."

                                        # İstifadəçinin cavabı
                                        user_choice = user_answers.get(q_id, (None, None))[0]

                                        # Status təyini
                                        if user_choice is None:
                                            status_icon = "⚪"
                                            status_text = "Cavablandırılmayıb"
                                        elif user_choice == correct_opt:
                                            status_icon = "✅"
                                            status_text = "Düzgün"
                                        else:
                                            status_icon = "❌"
                                            status_text = "Səhv"

                                        with st.expander(
                                                f"{status_icon} Sual {idx}: {q_text[:50]}... ({status_text})"
                                        ):
                                            st.markdown(f"**Sual {idx}:** {q_text}")

                                            for opt_key, opt_val in opts.items():
                                                if opt_key == correct_opt and opt_key == user_choice:
                                                    st.success(
                                                        f"**{opt_key}) {opt_val}**  *(Sizin düzgün cavabınız)*"
                                                    )
                                                elif opt_key == correct_opt:
                                                    st.info(f"**{opt_key}) {opt_val}**  *(Düzgün cavab)*")
                                                elif opt_key == user_choice:
                                                    st.error(
                                                        f"**{opt_key}) {opt_val}**  *(Sizin yanlış cavabınız)*"
                                                    )
                                                else:
                                                    st.write(f"{opt_key}) {opt_val}")

                                            # 💡 Sualın Həlli Düyməsi
                                            st.write("")
                                            with st.popover("💡 Sualın həlli", use_container_width=False):
                                                st.markdown("### 📝 Düzgün Həll Yolu:")
                                                st.info(f"**Düzgün cavab:** {correct_opt}) {opts.get(correct_opt, '')}")
                                                st.write(q_solution)

                                    st.divider()

                                    # 3. Bağlama düyməsi
                                    if st.button("Pəncərəni Bağla və Tamamla", use_container_width=True):
                                        st.rerun()