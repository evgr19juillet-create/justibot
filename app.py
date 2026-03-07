import streamlit as st
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests
import uuid

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Justibots",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROTECTION ANTI-COPIE (CSS STRICT) ---
st.markdown("""
<style>
    /* 1. Bloque la sélection sur TOUTE la page par défaut */
    html, body, [class*="css"] {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }
    
    /* 2. Réautorise la saisie UNIQUEMENT sur les champs actifs (pour que le client puisse taper son nom/problème) */
    input:not([disabled]), textarea:not([disabled]) {
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
        user-select: text !important;
    }

    /* 3. VERROUILLAGE ABSOLU de la case d'aperçu désactivée */
    textarea[disabled] {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
        pointer-events: none !important; /* Bloque tout clic à l'intérieur */
    }

    /* Autorise le défilement (scroll) autour de la case pour pouvoir lire la fin du texte */
    div[data-baseweb="textarea"] {
        overflow-y: auto !important;
    }

    /* 4. Rend le surlignage 100% invisible en cas de forçage du navigateur */
    textarea[disabled]::selection {
        background-color: transparent !important;
        color: inherit !important;
    }
</style>
<script> document.addEventListener('contextmenu', event => event.preventDefault()); </script>
""", unsafe_allow_html=True)

# --- 2. RÉCUPÉRATION DES SECRETS ---
try:
    api_key = st.secrets["GEMINI_KEY"]
    user_email = st.secrets["EMAIL_ADDRESS"]
    user_password = st.secrets["EMAIL_PASSWORD"]
    sumup_api_key = st.secrets["SUMUP_API_KEY"]
    sumup_merchant_code = st.secrets["SUMUP_MERCHANT_CODE"]
except Exception:
    st.error("⚠️ Les secrets (clés) ne sont pas configurés. Vérifiez sur Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. DÉTECTION AUTOMATIQUE DU MODÈLE (LE CORRECTIF MAGIQUE) ---
@st.cache_resource
def obtenir_modele():
    try:
        # Demande à Google la liste exacte des modèles autorisés pour CETTE clé
        modeles_autorises = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Cherche le meilleur modèle récent en priorité
        for nom in modeles_autorises:
            if '1.5-flash' in nom:
                return nom.replace('models/', '')
                
        # Sinon, prend le premier modèle disponible qui fonctionne
        if modeles_autorises:
            return modeles_autorises[0].replace('models/', '')
            
        return 'gemini-1.5-flash'
    except Exception:
        # Si erreur d'API, on met une valeur par défaut
        return 'gemini-1.5-flash'

MODELE_AUTORISE = obtenir_modele()

# --- LOGIQUE DE PAIEMENT ---
query_params = st.query_params
est_paye = query_params.get("payment") == "success"

# --- 4. FONCTIONS ---
def creer_paiement_sumup(montant=5.00):
    url = "https://api.sumup.com/v0.1/checkouts"
    headers = {
        "Authorization": f"Bearer {sumup_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "checkout_reference": str(uuid.uuid4()),
        "amount": montant,
        "currency": "EUR",
        "merchant_code": sumup_merchant_code,
        "description": "Génération de Mise en Demeure - Justibots",
        "return_url": "https://justibot.fr/?payment=success" 
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            checkout_id = response.json().get("id")
            return f"https://pay.sumup.com/b2c/screen/#/{checkout_id}"
        return None
    except:
        return None

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
    model = genai.GenerativeModel(MODELE_AUTORISE)
    try:
        prompt = f"Analyse ce problème juridique et classe-le. Réponds juste par la catégorie. Contexte: {text}"
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        return f"Erreur d'analyse IA : {str(e)}"

def generer_courrier(probleme, categorie, user_infos):
    model = genai.GenerativeModel(MODELE_AUTORISE)
    date_jour = datetime.now().strftime("%d/%m/%Y")
    prompt = f"""
    Agis comme un avocat expert en droit de la consommation français. Rédige une MISE EN DEMEURE formelle.
    EXPÉDITEUR: Nom : {user_infos['nom']}, Adresse : {user_infos['adresse']}, Ville : {user_infos['ville']}, Email : {user_infos['email']}
    DATE : {date_jour} | MOTIF : {categorie} | FAITS : "{probleme}"
    CONSIGNES : En-tête complet, ton ferme juridique, cite articles de loi, résolution sous 8 jours, menace tribunal, signature.
    """
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Erreur IA complète : {str(e)} (Modèle utilisé: {MODELE_AUTORISE})"

# --- 5. INTERFACE ---
with st.sidebar:
    st.title("🧭 Navigation")
    choix_page = st.radio("Aller vers :", ["✍️ Générateur de Courrier", "📚 Ressources Juridiques"])
    st.divider()
    
    # --- MINI DIAGNOSTIC POUR TOI ---
    st.caption("🔧 Diagnostic Technique (Invisible pour le client)")
    st.caption(f"Clé lue : {api_key[:8]}...")
    st.caption(f"Modèle branché : {MODELE_AUTORISE}")

if choix_page == "✍️ Générateur de Courrier":
    st.title("⚖️ Justibots : Assistant Juridique")
    
    with st.sidebar:
        st.header("👤 Vos Coordonnées")
        nom_client = st.text_input("Nom & Prénom")
        adresse_client = st.text_input("Adresse (Rue)")
        ville_client = st.text_input("Code Postal & Ville")
        email_client_perso = st.text_input("Votre Email")

    col1, col2 = st.columns([1, 1])
    with col1:
        message_litige = st.text_area("Expliquez la situation en détail...", height=250)
    with col2:
        email_sav = st.text_input("Email du SAV adverse")
        st.write("") 
        
        if st.button("Générer ma Mise en Demeure ⚡", type="primary", use_container_width=True):
            if not nom_client or not message_litige:
                st.error("⚠️ Merci de remplir au moins votre NOM et la DESCRIPTION du problème.")
            else:
                with st.spinner("L'avocat IA rédige votre courrier..."):
                    cat = analyse_ia(message_litige)
                    infos_client = {"nom": nom_client, "adresse": adresse_client, "ville": ville_client, "email": email_client_perso}
                    
                    # Génération et sauvegarde dans la session
                    resultat_courrier = generer_courrier(message_litige, cat, infos_client)
                    st.session_state['courrier'] = resultat_courrier
                    st.session_state['sujet'] = f"MISE EN DEMEURE - {cat} - {nom_client}"
                    
                    # Lien SumUp
                    lien_sumup = creer_paiement_sumup(montant=5.00)
                    if lien_sumup:
                        st.session_state['lien_paiement'] = lien_sumup
                        st.success("Courrier généré avec succès ! Lisez les instructions ci-dessous.")
                    else:
                        st.error("⚠️ Erreur de connexion avec le terminal de paiement SumUp.")

    if 'courrier' in st.session_state:
        st.divider()
        if not est_paye:
            st.subheader("🔒 Votre courrier est prêt !")
            st.warning("Pour débloquer l'envoi, le téléchargement et les modifications, merci de régler les frais de service.")
            
            st.text_area("Aperçu complet (Lecture seule, Copie désactivée) :", value=st.session_state['courrier'], height=400, disabled=True)
            
            if 'lien_paiement' in st.session_state:
                st.link_button("💳 Payer avec SumUp (5,00€) pour débloquer", st.session_state['lien_paiement'], type="primary", use_container_width=True)
                st.caption("Une fois le paiement effectué, vous serez redirigé automatiquement ici.")
        else:
            st.subheader("📝 Votre courrier débloqué")
            st.success("✅ Paiement confirmé ! Vous pouvez maintenant modifier et envoyer votre courrier.")
            courrier_final = st.text_area("Relisez et modifiez si besoin :", value=st.session_state['courrier'], height=400)
            sujet_final = st.text_input("Objet du mail :", value=st.session_state['sujet'])
            
            col_send, col_down = st.columns([1, 1])
            with col_down:
                st.download_button("📥 Télécharger le texte", data=courrier_final, file_name="Mise_en_demeure.txt", mime="text/plain", use_container_width=True)
            with col_send:
                if st.button("🚀 Envoyer le mail au SAV", use_container_width=True):
                    if not email_sav:
                        st.error("Il manque l'email du destinataire !")
                    else:
                        with st.spinner("Envoi en cours..."):
                            ok, msg = envoyer_mail(email_sav, sujet_final, courrier_final)
                            st.success(msg) if ok else st.error(msg)

elif choix_page == "📚 Ressources Juridiques":
    st.title("📚 Ressources & Droits")
    st.markdown("Guides rapides pour comprendre vos droits avant d'agir.")
    st.info("💡 Sélectionnez une rubrique pour en savoir plus dans le menu de gauche.")
