import streamlit as st
import psycopg2

st.set_page_config(page_title="ClassLevel LMS", page_icon="🚀", layout="wide")


# --- DATABASE CONNECTION ---
def get_db_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])


# Bazada cədvəlləri yoxlamaq / yaratmaq
try:
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id SERIAL PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL,
        class_level INT NOT NULL,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id SERIAL PRIMARY KEY,
        title VARCHAR(150) NOT NULL,
        class_level INT NOT NULL,
        content TEXT,
        file_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_results (
        id SERIAL PRIMARY KEY,
        student_name VARCHAR(100),
        class_level INT,
        quiz_id INT REFERENCES quizzes(id),
        score INT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()
    st.success("✅ Supabase PostgreSQL bazasına uğurla qoşuldu!")
except Exception as e:
    st.error(f"❌ Supabase Qoşulma Xətası: {e}")

# --- HEADER & ROLE SELECTION ---
st.title("🚀 ClassLevel - Təhsil Və Qiymətləndirmə Portalı")

role = st.sidebar.radio("Giriş Rolunu Seçin:", ["🏆 Şagird Portalı", "👨‍🏫 Müəllim Paneli (ADMIN)"])

# ==========================================
# 1. ŞAGİRD PORTALI (QEYDİYYAT VƏ İMTAHAN)
# ==========================================
if role == "🏆 Şagird Portalı":
    st.header("📚 Şagird Qeydiyyatı və İmtahan Portalı")

    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("Ad və Soyadınız:", placeholder="Məs: Əli Əliyev")
    with col2:
        student_class = st.selectbox("Sinfinizi seçin:", list(range(1, 12)), index=4)

    if student_name.strip():
        # Şagirdi bazada qeydiyyata almaq / yoxlamaq
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO students (full_name, class_level) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                (student_name.strip(), student_class)
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as ex:
            pass  # Xəta olarsa səssiz davam et və ya logla

        st.subheader(f"📖 {student_class}-ci Sinif üçün Aktiv Dərslər və Quizlər")

        # Sinfə uyğun dərsləri gətirmək
        available_lessons = []
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, title, content FROM lessons WHERE class_level = %s", (student_class,))
            available_lessons = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as ex:
            st.error(f"Dərslər yüklənərkən xəta: {ex}")

        if not available_lessons:
            st.warning(f"{student_class}-ci sinif üçün hələ ki bazada dərs və ya imtahan əlavə edilməyib.")
        else:
            lesson_dict = {l[0]: l[1] for l in available_lessons}
            selected_lesson_id = st.selectbox("Dərsi seçin:", list(lesson_dict.keys()),
                                              format_func=lambda x: lesson_dict[x])

            # Seçilmiş dərsin məzmununu göstər
            for l in available_lessons:
                if l[0] == selected_lesson_id:
                    st.info(f"**Dərs Mövzusu:** {l[1]}\n\n{l[2] if l[2]  else ''}")

            # Dərsə aid quizi gətir
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option FROM quizzes WHERE lesson_id = %s",
                    (selected_lesson_id,))
                questions = cur.fetchall()
                cur.close()
                conn.close()

                if questions:
                    st.write("---")
                    st.subheader("✍️ Quiz / İmtahan Sualları")
                    score = 0
                    with st.form("quiz_form"):
                        for idx, q in enumerate(questions, 1):
                            st.markdown(f"**Sual {idx}: {q[1]}**")
                            ans = st.radio(f"Cavabınızı seçin ({idx}):",
                                           [f"A) {q[2]}", f"B) {q[3]}", f"C) {q[4]}", f"D) {q[5]}"], key=f"q_{q[0]}")

                        submit_quiz = st.form_submit_button("İmtahanı Tamamla")
                        if submit_quiz:
                            st.success("İmtahan cavablarınız qeydə alındı!")
                else:
                    st.info("Bu dərs üzrə hələ ki imtahan sualı əlavə edilməyib.")
            except Exception as ex:
                st.error(f"Suallar yüklənərkən xəta: {ex}")
    else:
        st.info("İmtahana və dərslərə başlamaq üçün zəhmət olmasa yuxarıda ad və soyadınızı daxil edin.")

# ==========================================
# 2. MÜƏLLİM İDARƏETMƏ PANELSİ (ADMIN)
# ==========================================
elif role == "👨‍🏫 Müəllim Paneli (ADMIN)":
    st.header("🛠️ Müəllim İdarəetmə Paneli (ADMIN)")

    m_tab1, m_tab2, m_tab3 = st.tabs([
        "📊 Sinif Jurnalı & Analitika",
        "➕ Yeni Dərs və Fayl Əlavə Et",
        "❓ Vaxtlı Quiz Yarat"
    ])

    # TAB 1: Sinif Jurnalı və Şagird Siyahısı
    with m_tab1:
        st.subheader("🎓 Qeydiyyatdan Keçmiş Şagirdlər Siyahısı")
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, full_name, class_level, registered_at FROM students ORDER BY registered_at DESC")
            students = cur.fetchall()
            cur.close()
            conn.close()

            if students:
                st.dataframe(
                    [{"ID": s[0], "Ad Soyad": s[1], "Sinif": f"{s[2]}-ci sinif", "Tarix": s[3]} for s in students],
                    use_container_width=True
                )
            else:
                st.info("Hələ ki heç bir şagird sistemə daxil olmayıb.")
        except Exception as ex:
            st.error(f"Şagird siyahısı yüklənərkən xəta: {ex}")

    # TAB 2: Yeni Dərs Əlavə Et
    with m_tab2:
        st.subheader("📚 Bazaya Yeni Dərs Əlavə Et")
        with st.form("add_lesson_form"):
            lesson_title = st.text_input("Dərsin Adı / Mövzu:")
            target_class = st.selectbox("Hansi sinif üçün?", list(range(1, 12)), index=4)
            lesson_content = st.text_area("Dərs haqqında qısa qeyd / Mətn:")

            submit_lesson = st.form_submit_button("Dərsi Bazaya Əlavə Et")
            if submit_lesson:
                if lesson_title.strip():
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO lessons (title, class_level, content) VALUES (%s, %s, %s)",
                            (lesson_title.strip(), target_class, lesson_content)
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"'{lesson_title}' uğurla {target_class}-ci sinfə əlavə edildi!")
                    except Exception as ex:
                        st.error(f"Dərs əlavə edilərkən xəta: {ex}")
                else:
                    st.warning("Lütfən dərsin adını daxil edin.")

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
                st.info("Sual əlavə etmək üçün əvvəlcə ən azı 1 dərs əlavə edilməlidir.")
        except Exception as ex:
            st.error(f"Dərslər siyahısı yüklənərkən xəta: {ex}")