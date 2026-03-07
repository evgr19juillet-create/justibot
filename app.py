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

# --- PROTECTION ANTI-COPIE ET NETTOYAGE DESIGN (CSS & JS) ---
st.markdown("""
<style>
    /* 1. Bloque la sélection sur TOUTE la page par défaut */
    html, body, [class*="css"] {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }
    
    /* 2. Réautorise la saisie UNIQUEMENT sur les champs actifs */
    input:not([disabled]), textarea:not([disabled]) {
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
        user-select: text !important;
    }

    /* 3. VERROUILLAGE de la case d'aperçu SANS bloquer le scroll */
    textarea[disabled] {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }

    /* 4. Rend le surlignage invisible */
    textarea[disabled]::selection { background-color: transparent !important; color: inherit !important; }

    /* 5. CACHE TOUT STREAMLIT (Sécurité supplémentaire) */
    header, footer, [data-testid="stHeader"], [data-testid="stFooter"], [data-testid="stToolbar"], #MainMenu { display: none !important; visibility: hidden !important; }

    /* 6. METHODE SNIPER : CACHE LA BARRE DU MODE "EMBED/IFRAME" */
    a[href^="https://streamlit.io"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    button[title="View fullscreen"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    div[class^="viewerBadge"] { display: none !important; visibility: hidden !important; opacity: 0 !important; }
    .viewerBadge_container__1QSob { display: none !important; }
</style>
<script>
    /* Bloque le clic droit et les raccourcis de copie */
    document.addEventListener('contextmenu', event => event.preventDefault());
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'C' || e.key === 'a' || e.key === 'A' || e.key === 'x' || e.key === 'X')) {
            e.preventDefault();
        }
    });
    document.addEventListener('copy', function(e) { e.preventDefault(); });
</script>
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

# --- 3. DÉTECTION AUTOMATIQUE DU MODÈLE ---
@st.cache_resource
def obtenir_modele():
    try:
        modeles_autorises = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for nom in modeles_autorises:
            if '1.5-flash' in nom:
                return nom.replace('models/', '')
        if modeles_autorises:
            return modeles_autorises[0].replace('models/', '')
        return 'gemini-1.5-flash'
    except Exception:
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
        "return_url": "https://justibot.fr/?payment=success",
        "hosted_checkout": {"enabled": True}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            return response.json().get("hosted_checkout_url")
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
    
    # LA NOUVELLE CONSIGNE ULTRA-STRICTE POUR L'IA
    prompt = f"""
    Tu es un assistant juridique expert. Rédige une MISE EN DEMEURE complète et définitive.
    L'expéditeur et signataire direct de cette lettre est le client lui-même.

    RÈGLE ABSOLUE : Tu ne dois laisser AUCUN texte à trous ou entre crochets (pas de [Adresse] ou [Nom]). 
    Tu dois OBLIGATOIREMENT intégrer les informations suivantes dans l'en-tête, en haut à gauche de la lettre :
    Nom et Prénom : {user_infos['nom']}
    Adresse : {user_infos['adresse']}
    Ville : {user_infos['ville']}
    Email : {user_infos['email']}

    DATE DU JOUR : {date_jour}
    MOTIF DU LITIGE : {categorie}
    FAITS EXPLIQUÉS : "{probleme}"

    CONSIGNES DE RÉDACTION :
    1. Écris à la première personne du singulier ("Je").
    2. Adopte un ton formel, extrêmement ferme et menaçant sur le plan juridique.
    3. Cite impérativement les articles de loi adaptés à ce problème (Code de la Consommation, Code Civil...).
    4. Exige une résolution du problème sous 8 jours, sous peine de saisir la juridiction compétente.
    5. Intègre le nom du signataire ({user_infos['nom']}) à la fin de la lettre.
    Ne rajoute pas de blabla ou d'introduction de chatbot, génère uniquement le texte de la lettre.
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
                    
                    resultat_courrier = generer_courrier(message_litige, cat, infos_client)
                    st.session_state['courrier'] = resultat_courrier
                    st.session_state['sujet'] = f"MISE EN DEMEURE - {cat} - {nom_client}"
                    
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
