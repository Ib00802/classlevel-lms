import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Streamlit Səhifə Konfiqurasiyası
st.set_page_config(page_title="ClassLevel LMS Portal", page_icon="🚀", layout="wide")


# ---------------------------------------------------------
# POSTGRESQL (SUPABASE) BAĞLANTI FUNKSİYASI
# ---------------------------------------------------------
def get_db_connection():
    try:
        return psycopg2.connect(st.secrets["postgres"]["url"])
    except Exception as e:
        st.error(f"⚠️ PostgreSQL Bağlantı Xətası: {e}")
        # Müvəqqəti fallback
        import sqlite3
        return sqlite3.connect("lms_data.db", check_same_thread=False)

# ---------------------------------------------------------
# BAZA CƏDVƏLLƏRİNİ AVTOMATİK YARADAN FUNKSİYA (DAİMİ YADDAŞ)
# ---------------------------------------------------------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Dərslər (Lessons) Cədvəli
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id SERIAL PRIMARY KEY,
            class_level INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Suallar / Quiz Cədvəli
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id SERIAL PRIMARY KEY,
            lesson_id INT NOT NULL,
            quiz_title VARCHAR(255) NOT NULL,
            question_text TEXT NOT NULL,
            option_a VARCHAR(255) NOT NULL,
            option_b VARCHAR(255) NOT NULL,
            option_c VARCHAR(255) NOT NULL,
            option_d VARCHAR(255) NOT NULL,
            correct_option CHAR(1) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Şagirdlərin Qeydiyyat Cədvəli (Daimi Baza)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            class_level INT NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(full_name, class_level)
        );
    """)

    # Şagird İmtahan Nəticələri Cədvəli
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id SERIAL PRIMARY KEY,
            student_name VARCHAR(255) NOT NULL,
            class_level INT NOT NULL,
            quiz_title VARCHAR(255) NOT NULL,
            score INT NOT NULL,
            total_questions INT NOT NULL,
            percentage FLOAT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


# Tətbiq açılarkən cədvəlləri yoxla/yarat
try:
    init_db()
except Exception as e:
    st.error(f"Baza konfiqurasiya xətası: {e}")

# ---------------------------------------------------------
# ƏSAS İNTERFEYS VƏ ROL SEÇİMİ (MÜƏLLİM / ŞAGİRD)
# ---------------------------------------------------------
st.title("🚀 ClassLevel - Təhsil Və Qiymətləndirmə Portalı")
# PostgreSQL Bağlantı Yoxlanışı (Diaqnostika)
try:
    test_conn = psycopg2.connect(st.secrets["postgres"]["url"])
    st.success("✅ Supabase PostgreSQL bazasına uğurla qoşuldu!")
    test_conn.close()
except Exception as err:
    st.error(f"❌ Supabase Qoşulma Xətası: {err}")

role = st.sidebar.radio("Giriş Paneli Seçin:", ["👨‍🎓 Şagird Paneli", "👨‍🏫 Müəllim Paneli (ADMIN)"])

# =========================================================
# 1. ŞAGİRD PANELİ VƏ QEYDİYYAT
# =========================================================
if role == "👨‍🎓 Şagird Paneli":
    st.subheader("📚 Şagird İmtahan Portalı")

    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        student_name = st.text_input("Ad və Soyadınız:", placeholder="Məs: Əli Əliyev")
    with col_s2:
        student_class = st.selectbox("Sinfinizi seçin:", [5, 6, 7, 8, 9, 10, 11])

    if student_name.strip():
        # Şagirdi daimi olaraq bazaya qeyd etmək (təkrar düşməsin deyə ON CONFLICT DO NOTHING)
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO students (full_name, class_level)
                VALUES (%s, %s)
                ON CONFLICT (full_name, class_level) DO NOTHING;
            """, (student_name.strip(), student_class))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as ex:
            st.error(f"Şagird qeydiyyatı xətası: {ex}")

        # Şagirdin sinfinə uyğun dərsləri gətirmək
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, title FROM lessons WHERE class_level = %s", (student_class,))
            available_lessons = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as ex:
            available_lessons = []
            st.error(f"Dərslər yüklənərkən xəta: {ex}")

        if not available_lessons:
            st.warning(f"{student_class}-ci sinif üçün hələ ki bazada dərs əlavə edilməyib.")
        else:
            lesson_dict = {l[0]: l[1] for l in available_lessons}
            selected_lesson_id = st.selectbox("Dərsi seçin:", list(lesson_dict.keys()),
                                              format_func=lambda x: lesson_dict[x])

            # Seçilən dərsə uyğun Quiz-ləri gətirmək
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT quiz_title FROM quizzes WHERE lesson_id = %s", (selected_lesson_id,))
            available_quizzes = [r[0] for r in cur.fetchall()]
            cur.close()
            conn.close()

            if not available_quizzes:
                st.info("Bu dərs üzrə hələ quiz yaradılmayıb.")
            else:
                selected_quiz = st.selectbox("Quiz-i seçin:", available_quizzes)

                # Quiz suallarını çəkmək
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option 
                    FROM quizzes WHERE lesson_id = %s AND quiz_title = %s
                """, (selected_lesson_id, selected_quiz))
                questions = cur.fetchall()
                cur.close()
                conn.close()

                st.divider()
                st.markdown(f"### 📝 {selected_quiz} (Cəmi {len(questions)} sual)")

                user_answers = {}
                with st.form("quiz_form"):
                    for idx, q in enumerate(questions, 1):
                        q_id, q_text, op_a, op_b, op_c, op_d, corr = q
                        st.markdown(f"**Sual {idx}: {q_text}**")
                        user_answers[q_id] = {
                            "selected": st.radio(
                                f"Cavabınız (Sual {idx}):",
                                options=["A", "B", "C", "D"],
                                format_func=lambda
                                    x: f"{x}) {op_a if x == 'A' else op_b if x == 'B' else op_c if x == 'C' else op_d}",
                                key=f"q_{q_id}"
                            ),
                            "correct": corr
                        }
                        st.divider()

                    submit_quiz = st.form_submit_button("🎯 İmtahanı Bitir və Cavabları Göndər")

                if submit_quiz:
                    score = sum(1 for q_id, ans in user_answers.items() if ans["selected"] == ans["correct"])
                    total = len(questions)
                    percentage = round((score / total) * 100, 1) if total > 0 else 0

                    # Nəticəni Bazaya Yazmaq
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO quiz_results (student_name, class_level, quiz_title, score, total_questions, percentage)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (student_name.strip(), student_class, selected_quiz, score, total, percentage))
                        conn.commit()
                        cur.close()
                        conn.close()

                        st.balloons()
                        st.success(f"Təbrik edirik, {student_name}! İmtahanınız tamamlandı.")
                        st.metric(label="Topladığınız Bal", value=f"{score} / {total}", delta=f"{percentage}%")
                    except Exception as ex:
                        st.error(f"Nəticə yadda saxlanılarkən xəta: {ex}")
    else:
        st.info("İmtahana başlamaq üçün zəhmət olmasa yuxarıda ad və soyadınızı qeyd edin.")
        # =========================================================
        # 2. MÜƏLLİM PANELSİ (ADMIN)
        # =========================================================
        st.subheader("🛠️ Müəllim İdarəetmə Paneli (ADMIN)")

        m_tab1, m_tab2, m_tab3 = st.tabs([
            "📊 Sinif Jurnalı & Analitika",
            "➕ Yeni Dərs və Fayl Əlavə Et",
            "❓ Vaxtlı Quiz Yarat"
        ])

        # TAB 1: Jurnal, Şagird Siyahısı və Nəticələr
        with m_tab1:
            st.subheader("👨‍🎓 Qeydiyyatdan Keçmiş Şagirdlər Siyahısı")
            try:
                conn = get_db_connection()
                df_students = pd.read_sql("""
                        SELECT full_name AS "Şagird Adı", 
                               class_level AS "Sinif", 
                               registered_at AS "Qeydiyyat Tarixi" 
                        FROM students 
                        ORDER BY registered_at DESC
                    """, conn)
                conn.close()

                if df_students.empty:
                    st.info("Hələ ki heç bir şagird sistemə daxil olmayıb.")
                else:
                    st.dataframe(df_students, use_container_width=True)
            except Exception as ex:
                st.error(f"Şagird siyahısı oxunarkən xəta: {ex}")

            st.divider()
            st.subheader("📊 Şagirdlərin İmtahan Nəticələri")
            try:
                conn = get_db_connection()
                df_results = pd.read_sql("""
                        SELECT student_name AS "Şagird", 
                               class_level AS "Sinif", 
                               quiz_title AS "Quiz", 
                               score AS "Doğru Cavab", 
                               total_questions AS "Cəmi Sual", 
                               percentage AS "Faiz (%)", 
                               completed_at AS "Tarix" 
                        FROM quiz_results 
                        ORDER BY completed_at DESC
                    """, conn)
                conn.close()

                if df_results.empty:
                    st.info("Hələ ki heç bir şagird imtahan verməyib.")
                else:
                    st.dataframe(df_results, use_container_width=True)
            except Exception as ex:
                st.error(f"Nəticələr oxunarkən xəta: {ex}")

        # TAB 2: Yeni Dərs Əlavə Etmə
        with m_tab2:
            st.subheader("➕ Yeni Dərs Mövzusu Əlavə Et")
            with st.form("add_lesson_form", clear_on_submit=True):
                col_l1, col_l2 = st.columns([1, 2])
                with col_l1:
                    lesson_class = st.selectbox("Sinif seçin:", [5, 6, 7, 8, 9, 10, 11], key="l_class")
                with col_l2:
                    lesson_title = st.text_input("Dərs / Mövzu Başlığı:", placeholder="Məs: İnformasiya və proseslər")

                submit_l_btn = st.form_submit_button("Dərsi Bazaya Saxla")

                if submit_l_btn:
                    if lesson_title.strip():
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO lessons (class_level, title) VALUES (%s, %s)",
                                           (lesson_class, lesson_title.strip()))
                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.success(
                                f"'{lesson_title}' dərsi {lesson_class}-ci sinif üçün uğurla bazaya əlavə edildi!")
                        except Exception as ex:
                            st.error(f"Dərs əlavə edilərkən xəta yarandı: {ex}")
                    else:
                        st.warning("Lütfən dərs başlığını daxil edin.")

        # TAB 3: Quiz Yaratmaq
        with m_tab3:
            st.subheader("❓ Dərsə Vaxtlı Quiz və Çoxlu Sual Əlavə Et")
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT lesson_id, title, class_level FROM lessons ORDER BY class_level, lesson_id")
                all_l = cursor.fetchall()
                cursor.close()
                conn.close()
            except Exception as e:
                all_l = []
                st.error(f"Baza bağlantı xətası: {e}")

            if not all_l:
                st.warning("Bazada dərs yoxdur! Əvvəlcə 'Yeni Dərs və Fayl Əlavə Et' tabından dərs əlavə edin.")
            else:
                l_dict = {r[0]: f"{r[2]}-ci Sinif: {r[1]}" for r in all_l}
                target_l_id = st.selectbox("Dərsi seçin:", list(l_dict.keys()), format_func=lambda x: l_dict[x])

                col_q1, col_q2 = st.columns([2, 1])
                with col_q1:
                    q_title_input = st.text_input("Quiz Başlığı (Məs: Quiz 1, Sınaq 2):", value="Quiz 1")
                with col_q2:
                    q_time_limit = st.number_input("Həlletmə müddəti (Dəqiqə):", min_value=1, max_value=180, value=10)

                st.divider()

                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM quizzes WHERE lesson_id = %s AND quiz_title = %s",
                                   (target_l_id, q_title_input))
                    q_count = cursor.fetchone()[0]
                    cursor.close()
                    conn.close()
                except Exception as ex:
                    q_count = 0

                st.info(f"📌 **{q_title_input}** üçün bazada hazırda **{q_count} sual** var.")

                with st.form(key="add_question_form", clear_on_submit=True):
                    st.markdown(f"### 📝 Sual #{q_count + 1}")
                    q_txt = st.text_area("Sualın Mətni:", placeholder="Sualı bura daxil edin...")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        qa = st.text_input("A variantı:")
                        qc = st.text_input("C variantı:")
                    with col_b:
                        qb = st.text_input("B variantı:")
                        qd = st.text_input("D variantı:")

                    q_corr = st.selectbox("Doğru Cavab Variantını Seçin:", ["A", "B", "C", "D"])

                    submit_button = st.form_submit_button(label="➕ Sualı Yadda Saxla və Növbəti Suala Keç")

                    if submit_button:
                        if q_txt.strip() and qa.strip() and qb.strip() and qc.strip() and qd.strip():
                            try:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                        INSERT INTO quizzes 
                                        (lesson_id, quiz_title, question_text, option_a, option_b, option_c, option_d, correct_option)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (target_l_id, q_title_input, q_txt.strip(), qa.strip(), qb.strip(), qc.strip(),
                                          qd.strip(), q_corr))
                                conn.commit()
                                cursor.close()
                                conn.close()

                                st.success(f"Sual #{q_count + 1} uğurla yadda saxlanıldı!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Sual yazılarkən xəta: {ex}")
                        else:
                            st.warning("Zəhmət olmasa sual mətnini və bütün variantları tam doldurun.")