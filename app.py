import streamlit as st
import psycopg2
import hashlib
import pandas as pd

# --- SƏHİFƏNİN KONFİQURASİYASI ---
st.set_page_config(page_title="ClassLevel LMS", page_icon="🎓", layout="wide")


# --- KÖMƏKÇİ FUNKSİYALAR VƏ BAZA BAĞLANTISI ---
# QEYD: Bura öz PostgreSQL məlumatlarınızı daxil edin
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="your_database_name",
        user="your_db_user",
        password="your_db_password"
    )


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False


def create_results_table():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255),
                package_id INT,
                correct_count INT,
                wrong_count INT,
                empty_count INT,
                score_percent FLOAT,
                attempt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Baza xətası: {e}")


# Proqram işə düşəndə nəticə cədvəlinin mövcudluğunu yoxlayır və yaradır
create_results_table()

# --- SESSİYA (SESSION STATE) DƏYİŞƏNLƏRİ ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "full_name" not in st.session_state:
    st.session_state["full_name"] = ""
if "user_role" not in st.session_state:
    st.session_state["user_role"] = ""
if "class_level" not in st.session_state:
    st.session_state["class_level"] = 5
if "student_page" not in st.session_state:
    st.session_state["student_page"] = "Əsas səhifə"

# ==========================================
# GİRİŞ VƏ QEYDİYYAT SƏHİFƏSİ
# ==========================================
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
    # ==========================================
    # SİSTEMƏ DAXİL OLDUQDAN SONRAKİ EKRAN
    # ==========================================
else:
    # --- SOL MENYU (SIDEBAR) ---
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

    # --- MÜƏLLİM (ADMİN) PANELİ ---
    if st.session_state['user_role'] == 'admin':
        st.header("Müəllim İdarəetmə Paneli")
        m_t1, m_t2, m_t3 = st.tabs(["👥 Şagirdlər", "📚 Materiallar", "📝 Quiz Paketi Yarat"])

        # (Sizin köhnə m_t1 və m_t2 kodlarınız bura gələcək)
        with m_t1:
            st.write("Şagirdlərin siyahısı və idarəedilməsi.")
        with m_t2:
            st.write("Dərs materiallarının yüklənməsi.")

        with m_t3:
            st.subheader("Quiz Paketi və Sualların Tərtibi")

            # 1. Addım: Yeni Quiz Paketi Yaratmaq
            with st.form("new_pack_form"):
                st.markdown("### 1. Yeni Quiz Paketi Başlığı Yarat")
                qp_class = st.selectbox("Hansı Sinif Üçün?", list(range(1, 12)), index=8, key="qp_cl_new")
                qp_title = st.text_input("Quiz Adı (Məsələn: Quiz 1 - İnformatika Giriş):")
                qp_diff = st.selectbox("Çətinlik Səviyyəsi:", ["Asan", "Orta", "Çətin"], key="qp_df_new")
                qp_dur = st.number_input("Ümumi Vaxt (dəqiqə ilə):", min_value=1, value=10, key="qp_dr_new")

                if st.form_submit_button("Yeni Quiz Paketi Əlavə Et"):
                    if qp_title:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                "INSERT INTO quiz_packages (class_level, title, difficulty, duration_minutes) VALUES (%s, %s, %s, %s)",
                                (qp_class, qp_title, qp_diff, int(qp_dur)))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(
                                "Quiz paketi yaradıldı! İndi aşağıdan həmin paketə suallar əlavə edə bilərsiniz.")
                            st.rerun()
                        except Exception as e:
                            st.error(e)
                    else:
                        st.warning("Zəhmət olmasa quiz adını daxil edin.")

            st.write("---")

            # 2. Addım: Mövcud Paketlərə İstədiyiniz Qədər Sual Əlavə Etmək
            st.markdown("### 2. Mövcud Quizə Sual Əlavə Et")
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, title, class_level FROM quiz_packages ORDER BY id DESC")
                all_packs = cur.fetchall()
                cur.close()
                conn.close()

                if all_packs:
                    pack_options = {p[0]: f"{p[1]} ({p[2]}-ci sinif)" for p in all_packs}
                    selected_pack_id = st.selectbox("Sual əlavə olunacaq Quizi seçin:", list(pack_options.keys()),
                                                    format_func=lambda x: pack_options[x], key="sel_pack_for_q")

                    with st.form("add_questions_form", clear_on_submit=True):
                        q_text = st.text_area("Sual Mətni:", key="qa_text")
                        opt_a = st.text_input("Variant A:", key="qa_a")
                        opt_b = st.text_input("Variant B:", key="qa_b")
                        opt_c = st.text_input("Variant C:", key="qa_c")
                        opt_d = st.text_input("Variant D:", key="qa_d")
                        cor_opt = st.selectbox("Düzgün Variant:", ["A", "B", "C", "D"], key="qa_cor")

                        if st.form_submit_button("Bu Quizə Sualı Əlavə Et"):
                            if q_text and opt_a and opt_b:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute("""
                                      INSERT INTO quiz_questions (package_id, question_text, option_a, option_b, option_c, option_d, correct_option)
                                      VALUES (%s, %s, %s, %s, %s, %s, %s)
                                  """, (selected_pack_id, q_text, opt_a, opt_b, opt_c, opt_d, cor_opt))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success("Sual uğurla əlavə olundu!")
                                st.rerun()
                            else:
                                st.warning("Sual mətni və variantlar boş ola bilməz.")
                else:
                    st.info("Əvvəlcə yuxarıdan yeni quiz paketi yaradın.")
            except Exception as e:
                st.error(e)

    # --- ŞAGİRD PANELİ ---
    elif st.session_state['user_role'] == 'student':
        if st.session_state.get("student_page") == "Əsas səhifə":
            st.header("🏠 Əsas Səhifə")
            st.write("Sizin əsas məlumatlarınız və elanlar burada görünəcək.")

        elif st.session_state.get("student_page") == "Materiallar":
            st.header("📚 Dərs Materialları")
            st.write("Müəlliminizin yüklədiyi materiallar burada olacaq.")

        elif st.session_state.get("student_page") == "Quizlər":
            st.header("✍️ Quizlər və İmtahanlar")

            student_class = st.session_state['class_level']
            username = st.session_state['username']

            try:
                conn = get_db_connection()
                cur = conn.cursor()

                # Yalnız son 3 gündə İŞLƏNMƏYƏN quizləri çəkirik
                cur.execute("""
                      SELECT id, title, duration_minutes 
                      FROM quiz_packages 
                      WHERE class_level = %s 
                      AND id NOT IN (
                          SELECT package_id 
                          FROM quiz_results 
                          WHERE username = %s AND attempt_date >= NOW() - INTERVAL '3 days'
                      )
                      ORDER BY id DESC
                  """, (student_class, username))
                available_quizzes = cur.fetchall()

                if not available_quizzes:
                    st.info(
                        "Hazırda sizin üçün aktiv quiz paketi mövcud deyil və ya mövcud quizləri artıq işləmisiniz (Növbəti cəhd üçün 3 gün gözləməlisiniz).")
                else:
                    quiz_options = {q[0]: f"{q[1]} ({q[2]} dəqiqə)" for q in available_quizzes}
                    selected_quiz = st.selectbox("İşləmək istədiyiniz quizi seçin:", list(quiz_options.keys()),
                                                 format_func=lambda x: quiz_options[x])

                    if st.button("Quizi Başlat", use_container_width=True):
                        st.session_state['active_quiz'] = selected_quiz
                        st.session_state['quiz_submitted'] = False
                        st.rerun()

                # ==========================================
                # AKTİV QUİZ VƏ BAXIŞ REJİMİ
                # ==========================================
                if 'active_quiz' in st.session_state and st.session_state['active_quiz'] is not None:
                    active_q_id = st.session_state['active_quiz']

                    cur.execute("""
                          SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option 
                          FROM quiz_questions 
                          WHERE package_id = %s
                      """, (active_q_id,))
                    questions = cur.fetchall()

                    if not questions:
                        st.warning("Bu quiz paketində hələ sual yoxdur.")
                    else:
                        # 1. QUİZİ İŞLƏMƏ MƏRHƏLƏSİ
                        if not st.session_state.get('quiz_submitted', False):
                            st.write("---")
                            st.subheader("Uğurlar! Sualları diqqətlə oxuyun.")

                            with st.form("take_quiz_form"):
                                user_answers = {}
                                for idx, q in enumerate(questions):
                                    st.markdown(f"**Sual {idx + 1}:** {q[1]}")
                                    opts = ["Cavablandırmaq istəmirəm", f"A) {q[2]}", f"B) {q[3]}", f"C) {q[4]}",
                                            f"D) {q[5]}"]
                                    ans = st.radio("Variant seçin:", opts, key=f"q_ans_{q[0]}",
                                                   label_visibility="collapsed")
                                    user_answers[q[0]] = ans
                                    st.write("---")

                                if st.form_submit_button("Quizi Bitir və Nəticəni Gör", type="primary",
                                                         use_container_width=True):
                                    correct_n = 0
                                    wrong_n = 0
                                    empty_n = 0
                                    detailed_results = []

                                    for q in questions:
                                        correct_letter = q[6]
                                        u_ans_full = user_answers[q[0]]

                                        if u_ans_full == "Cavablandırmaq istəmirəm":
                                            empty_n += 1
                                            u_letter = "Boş"
                                        else:
                                            u_letter = u_ans_full[0]
                                            if u_letter == correct_letter:
                                                correct_n += 1
                                            else:
                                                wrong_n += 1

                                        detailed_results.append({
                                            'q_text': q[1],
                                            'opts': {'A': q[2], 'B': q[3], 'C': q[4], 'D': q[5]},
                                            'correct': correct_letter,
                                            'user': u_letter
                                        })

                                    total_q = len(questions)
                                    score_perc = (correct_n / total_q) * 100 if total_q > 0 else 0

                                    # Bazaya qeyd (3 günlük bloklama üçün)
                                    try:
                                        cur.execute("""
                                              INSERT INTO quiz_results (username, package_id, correct_count, wrong_count, empty_count, score_percent)
                                              VALUES (%s, %s, %s, %s, %s, %s)
                                          """, (username, active_q_id, correct_n, wrong_n, empty_n, score_perc))
                                        conn.commit()
                                    except Exception as ex:
                                        st.error(f"Nəticə yazılarkən xəta: {ex}")

                                    st.session_state['quiz_submitted'] = True
                                    st.session_state['quiz_stats'] = {
                                        "Düzgün": correct_n, "Səhv": wrong_n, "Cavablandırılmamış": empty_n,
                                        "Nəticə (%)": round(score_perc, 1)
                                    }
                                    st.session_state['quiz_details'] = detailed_results
                                    st.rerun()

                        # 2. TƏHLİL VƏ BAXIŞ REJİMİ
                        else:
                            st.success(
                                "Təbrik edirik! Quizi bitirdiniz. Bu quiz növbəti 3 gün ərzində sizin üçün əlçatmaz olacaq.")

                            st.subheader("📊 Ümumi Nəticəniz")
                            stats = st.session_state['quiz_stats']
                            df = pd.DataFrame([stats])
                            st.dataframe(df, use_container_width=True, hide_index=True)

                            st.write("---")
                            st.subheader("🔍 Suallara Baxış (Səhv və Düzlərinizin Təhlili)")

                            details = st.session_state['quiz_details']
                            for idx, item in enumerate(details):
                                st.markdown(f"**Sual {idx + 1}:** {item['q_text']}")

                                for letter, text in item['opts'].items():
                                    if letter == item['correct']:
                                        st.markdown(
                                            f"<div style='padding:10px; border-radius:5px; background-color:#dcfce7; color:#166534; margin-bottom:5px;'>✅ <b>{letter})</b> {text} (Düzgün Cavab)</div>",
                                            unsafe_allow_html=True)
                                    elif letter == item['user'] and item['user'] != item['correct']:
                                        st.markdown(
                                            f"<div style='padding:10px; border-radius:5px; background-color:#fee2e2; color:#991b1b; margin-bottom:5px;'>❌ <b>{letter})</b> {text} (Sizin Seçiminiz)</div>",
                                            unsafe_allow_html=True)
                                    else:
                                        st.markdown(
                                            f"<div style='padding:10px; border-radius:5px; background-color:#f1f5f9; color:#475569; margin-bottom:5px;'>⚪ <b>{letter})</b> {text}</div>",
                                            unsafe_allow_html=True)

                                if item['user'] == "Boş":
                                    st.markdown(
                                        "<span style='color:#ea580c; font-weight:bold;'>⚠️ Siz bu sualı cavabsız buraxmısınız.</span>",
                                        unsafe_allow_html=True)

                                st.write("---")

                            if st.button("Ana Səhifəyə Qayıt", use_container_width=True):
                                st.session_state['active_quiz'] = None
                                st.session_state['quiz_submitted'] = False
                                st.session_state["student_page"] = "Əsas səhifə"
                                st.rerun()

                cur.close()
                conn.close()
            except Exception as e:
                st.error(f"Sistem xətası: {e}")