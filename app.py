import streamlit as st
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Justibots",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. RÉCUPÉRATION DES SECRETS ---
try:
    api_key = st.secrets["GEMINI_KEY"]
    user_email = st.secrets["EMAIL_ADDRESS"]
    user_password = st.secrets["EMAIL_PASSWORD"]
except Exception:
    st.error("⚠️ Les secrets (clés) ne sont pas configurés dans Streamlit Settings > Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. FONCTIONS ---

def envoyer_mail(destinataire, sujet, corps):
    msg = MIMEMultipart()
    msg['From'] = user_email
    msg['To'] = destinataire
    msg['Subject'] = sujet
    msg.attach(MIMEText(corps, 'plain'))

    try:
        server = smtplib.SMTP('smtp.hostinger.com', 587)
        server.starttls()
        server.login(user_email, user_password)
        server.send_message(msg)
        server.quit()
        return True, "✅ Courrier envoyé avec succès !"
    except Exception as e:
        return False, f"Erreur d'envoi : {str(e)}"

def analyse_ia(text):
    # Utilisation du nom de modèle complet avec préfixe
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    try:
        prompt = f"Analyse ce problème juridique et classe-le (ex: Remboursement, Non-livraison, Vice caché). Réponds juste par la catégorie en 2 ou 3 mots. Contexte: {text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Litige de consommation"

def generer_courrier(probleme, categorie, user_infos):
    # Utilisation du nom de modèle complet avec préfixe
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    date_jour = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    Agis comme un avocat expert en droit de la consommation français.
    Rédige une MISE EN DEMEURE formelle et juridique.
    
    EXPÉDITEUR :
    Nom : {user_infos['nom']}
    Adresse : {user_infos['adresse']}, {user_infos['ville']}
    Email : {user_infos['email']}
    
    DATE : {date_jour}
    MOTIF : {categorie}
    DÉTAILS : "{probleme}"
    
    CONSIGNES :
    1. Ton ferme et professionnel.
    2. Cite les articles du Code de la Consommation (ex: L211-4, L217-4).
    3. Exige une solution sous 8 jours.
    4. Menace de poursuites judiciaires.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erreur de génération : {str(e)}"

# --- 4. INTERFACE ---

with st.sidebar:
    st.title("🧭 Navigation")
    choix_page = st.radio("Aller vers :", ["✍️ Générateur de Courrier", "📚 Ressources Juridiques"])
    st.divider()

if choix_page == "✍️ Générateur de Courrier":
    st.title("⚖️ Justibots : Assistant Juridique")
    
    with st.sidebar:
        st.header("👤 Vos Coordonnées")
        nom_client = st.text_input("Nom & Prénom", placeholder="Jean Dupont")
        adresse_client = st.text_input("Adresse", placeholder="10 rue de la Paix")
        ville_client = st.text_input("Code Postal & Ville", placeholder="75000 Paris")
        email_client_perso = st.text_input("Votre Email", placeholder="jean@mail.com")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Décrivez le problème")
        message_litige = st.text_area("Expliquez ici...", height=200)

    with col2:
        st.subheader("2. Destinataire")
        email_sav = st.text_input("Email du SAV adverse")
        
        if st.button("Générer le courrier ⚡", type="primary", use_container_width=True):
            if not nom_client or not message_litige:
                st.warning("Veuillez remplir votre nom et le problème.")
            else:
                with st.spinner("L'IA rédige..."):
                    cat = analyse_ia(message_litige)
                    infos = {"nom": nom_client, "adresse": adresse_client, "ville": ville_client, "email": email_client_perso}
                    courrier = generer_courrier(message_litige, cat, infos)
                    st.session_state['courrier'] = courrier
                    st.session_state['sujet'] = f"MISE EN DEMEURE - {cat}"

    if 'courrier' in st.session_state:
        st.divider()
        courrier_final = st.text_area("Courrier généré :", value=st.session_state['courrier'], height=350)
        sujet_final = st.text_input("Sujet du mail :", value=st.session_state['sujet'])
        
        if st.button("🚀 Envoyer par Email"):
            if not email_sav:
                st.error("Email du SAV manquant.")
            else:
                ok, res = envoyer_mail(email_sav, sujet_final, courrier_final)
                if ok: st.success(res)
                else: st.error(res)

elif choix_page == "📚 Ressources Juridiques":
    st.title("📚 Vos Droits")
    st.info("Consultez SignalConso.gouv.fr pour signaler une fraude.")
    with st.expander("Garantie de conformité"):
        st.write("Valable 2 ans pour tout produit neuf.")
