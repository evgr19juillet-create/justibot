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
    st.error("⚠️ Les secrets ne sont pas configurés. Allez dans Settings > Secrets sur Streamlit Cloud.")
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
        # Configuration spécifique pour Hostinger
        server = smtplib.SMTP('smtp.hostinger.com', 587)
        server.starttls()
        server.login(user_email, user_password)
        server.send_message(msg)
        server.quit()
        return True, "✅ Courrier envoyé avec succès !"
    except Exception as e:
        return False, f"Erreur d'envoi : {str(e)}"

def analyse_ia(text):
    # CORRECTION : Utilisation du modèle gemini-1.5-flash
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        prompt = f"Analyse ce problème juridique et classe-le (ex: Remboursement, Non-livraison, Vice caché). Réponds juste par la catégorie. Contexte: {text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Litige commercial"

def generer_courrier(probleme, categorie, user_infos):
    # CORRECTION : Utilisation du modèle gemini-1.5-flash
    model = genai.GenerativeModel('gemini-1.5-flash')
    date_jour = datetime.now().strftime("%d/%m/%Y")
    
    prompt = f"""
    Agis comme un avocat expert en droit de la consommation français.
    Rédige une MISE EN DEMEURE formelle et juridique.
    
    EXPÉDITEUR :
    Nom : {user_infos['nom']}
    Adresse : {user_infos['adresse']}
    Ville : {user_infos['ville']}
    Email : {user_infos['email']}
    
    DATE : {date_jour}
    MOTIF DU LITIGE : {categorie}
    DÉTAILS DES FAITS : "{probleme}"
    
    CONSIGNES DE RÉDACTION :
    1. Ton ferme et juridique.
    2. Citer les articles pertinents du Code de la Consommation.
    3. Exiger une résolution sous 8 jours sous peine de poursuites.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erreur IA : {str(e)}"

# --- 4. INTERFACE ---

with st.sidebar:
    st.title("🧭 Navigation")
    choix_page = st.radio("Aller vers :", ["✍️ Générateur de Courrier", "📚 Ressources Juridiques"])
    st.divider()

if choix_page == "✍️ Générateur de Courrier":
    st.title("⚖️ Justibots : Assistant Juridique")
    
    with st.sidebar:
        st.header("👤 Vos Coordonnées")
        nom_client = st.text_input("Nom & Prénom")
        adresse_client = st.text_input("Adresse")
        ville_client = st.text_input("Code Postal & Ville")
        email_client_perso = st.text_input("Votre Email")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Le Problème")
        message_litige = st.text_area("Décrivez la situation...", height=250)
    with col2:
        st.subheader("2. Le Destinataire")
        email_sav = st.text_input("Email du SAV adverse")
        
        if st.button("Générer ma Mise en Demeure ⚡", type="primary", use_container_width=True):
            if not nom_client or not message_litige:
                st.error("Veuillez remplir les informations manquantes.")
            else:
                with st.spinner("Rédaction en cours..."):
                    cat = analyse_ia(message_litige)
                    infos = {"nom": nom_client, "adresse": adresse_client, "ville": ville_client, "email": email_client_perso}
                    st.session_state['courrier'] = generer_courrier(message_litige, cat, infos)
                    st.session_state['sujet'] = f"MISE EN DEMEURE - {cat}"

    if 'courrier' in st.session_state:
        st.divider()
        courrier_final = st.text_area("Vérifiez le texte :", value=st.session_state['courrier'], height=400)
        if st.button("🚀 Envoyer le mail"):
            ok, msg = envoyer_mail(email_sav, st.session_state['sujet'], courrier_final)
            if ok: st.success(msg)
            else: st.error(msg)

elif choix_page == "📚 Ressources Juridiques":
    st.title("📚 Ressources Juridiques")
    st.write("Consultez vos droits sur SignalConso ou le Code de la consommation.")
