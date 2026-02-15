import streamlit as st
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
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
except FileNotFoundError:
    st.error("⚠️ Les secrets (clés) ne sont pas configurés. Vérifiez sur Streamlit.")
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
    # CORRECTION : Utilisation du modèle standard pour éviter l'erreur 404
    model = genai.GenerativeModel('gemini-pro')
    try:
        prompt = f"Analyse ce problème juridique et classe-le (ex: Remboursement, Non-livraison, Vice caché). Réponds juste par la catégorie. Contexte: {text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Litige commercial"

def generer_courrier(probleme, categorie, user_infos):
    # CORRECTION : Utilisation du modèle standard
    model = genai.GenerativeModel('gemini-pro')
    date_jour = datetime.now().strftime("%d/%m/%Y")
    
    # Construction du prompt avec les infos du formulaire
    prompt = f"""
    Agis comme un avocat expert en droit de la consommation français.
    Rédige une MISE EN DEMEURE formelle et menaçante.
    
    EXPÉDITEUR (MON CLIENT) :
    Nom : {user_infos['nom']}
    Adresse : {user_infos['adresse']}
    Ville : {user_infos['ville']}
    Email : {user_infos['email']}
    
    DATE : {date_jour}
    MOTIF DU LITIGE : {categorie}
    DÉTAILS DES FAITS : "{probleme}"
    
    CONSIGNES DE RÉDACTION :
    1. Commence par l'en-tête complet (Expéditeur en haut à gauche).
    2. Utilise un ton ferme, juridique et cite les articles du Code de la Consommation ou Code Civil pertinents.
    3. Exige une résolution sous 8 jours.
    4. Menace de saisir le médiateur ou le tribunal compétent.
    5. Termine par la signature (Nom du client).
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erreur IA : {e}"

# --- 4. INTERFACE ---

# --- NAVIGATION DANS LA SIDEBAR ---
with st.sidebar:
    st.title("🧭 Navigation")
    choix_page = st.radio("Aller vers :", ["✍️ Générateur de Courrier", "📚 Ressources Juridiques"])
    st.divider()

# ==========================================
# PAGE 1 : GÉNÉRATEUR
# ==========================================
if choix_page == "✍️ Générateur de Courrier":
    
    st.title("⚖️ Justibots : Assistant Juridique")
    st.markdown("Remplissez vos infos, décrivez le problème, et laissez l'IA rédiger la mise en demeure.")

    # --- BARRE LATÉRALE (FORMULAIRE CLIENT) ---
    with st.sidebar:
        st.header("👤 Vos Coordonnées")
        st.info("Ces informations sont nécessaires pour la validité du courrier.")
        
        nom_client = st.text_input("Nom & Prénom", placeholder="Jean Dupont")
        adresse_client = st.text_input("Adresse (Rue)", placeholder="10 rue de la Liberté")
        ville_client = st.text_input("Code Postal & Ville", placeholder="75000 Paris")
        email_client_perso = st.text_input("Votre Email (pour signature)", placeholder="jean.dupont@email.com")
        
        st.divider()
        
        # --- SECTION DONATION (SIDEBAR) ---
        st.subheader("☕ Soutenir le projet")
        st.caption("L'application est 100% gratuite. Un petit soutien fait toujours plaisir !")
        st.link_button(
            "❤️ Faire un don libre", 
            "https://buy.stripe.com/test_cNi28rdpobCU6Pe6q5bbG00", 
            type="secondary",
            use_container_width=True
        )

    # --- ZONE PRINCIPALE ---
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Le Problème")
        message_litige = st.text_area("Expliquez la situation en détail...", height=250, placeholder="J'ai acheté un iPhone le 10 janvier, il ne marche plus et le vendeur refuse le retour...")

    with col2:
        st.subheader("2. Le Destinataire (SAV)")
        email_sav = st.text_input("Email du SAV adverse", placeholder="sav@vendeur.com")
        
        st.write("") # Espace
        st.write("") 
        
        # Bouton de génération
        if st.button("Générer ma Mise en Demeure ⚡", type="primary", use_container_width=True):
            if not nom_client or not message_litige:
                st.error("⚠️ Merci de remplir au moins votre NOM et la DESCRIPTION du problème.")
            else:
                with st.spinner("L'avocat IA rédige votre courrier..."):
                    # 1. Analyse
                    cat = analyse_ia(message_litige)
                    # 2. Rédaction
                    infos_client = {
                        "nom": nom_client,
                        "adresse": adresse_client,
                        "ville": ville_client,
                        "email": email_client_perso
                    }
                    courrier_genere = generer_courrier(message_litige, cat, infos_client)
                    
                    # Stockage dans la session
                    st.session_state['courrier'] = courrier_genere
                    st.session_state['sujet'] = f"MISE EN DEMEURE - {cat} - Dossier {nom_client}"
                    st.success("Courrier généré avec succès ! Vérifiez ci-dessous.")

    # --- ZONE DE RÉSULTAT ET ENVOI ---
    if 'courrier' in st.session_state:
        st.divider()
        st.subheader("📝 Votre courrier est prêt")
        
        # Zone éditable
        courrier_final = st.text_area("Relisez et modifiez si besoin :", value=st.session_state['courrier'], height=400)
        sujet_final = st.text_input("Objet du mail :", value=st.session_state['sujet'])
        
        col_send, col_space = st.columns([1, 2])
        with col_send:
            if st.button("🚀 Envoyer le mail maintenant"):
                if not email_sav:
                    st.error("Il manque l'email du destinataire (SAV) !")
                else:
                    with st.spinner("Envoi en cours via Hostinger..."):
                        ok, msg = envoyer_mail(email_sav, sujet_final, courrier_final)
                        if ok:
                            st.balloons()
                            st.success(msg)
                            
                            # --- APPEL AU DON APRÈS SUCCÈS ---
                            st.markdown("---")
                            st.markdown("### 👏 Mission accomplie !")
                            st.info("Votre mise en demeure a été envoyée ! Si ce service vous a aidé, pensez à offrir un café au développeur.")
                            
                            col_vide, col_btn, col_vide2 = st.columns([1, 2, 1])
                            with col_btn:
                                st.link_button(
                                    "🏆 Offrir un café de la victoire", 
                                    "https://buy.stripe.com/test_cNi28rdpobCU6Pe6q5bbG00", 
                                    type="primary",
                                    use_container_width=True
                                )
                        else:
                            st.error(msg)

# ==========================================
# PAGE 2 : RESSOURCES JURIDIQUES
# ==========================================
elif choix_page == "📚 Ressources Juridiques":
    st.title("📚 Ressources & Droits du Consommateur")
    st.markdown("Guides rapides pour comprendre vos droits avant d'agir.")
    
    # --- Barre latérale simplifiée pour cette page ---
    with st.sidebar:
         st.info("💡 Sélectionnez une rubrique pour en savoir plus.")
         st.divider()
         st.link_button(
            "❤️ Soutenir le projet", 
            "https://buy.stripe.com/test_cNi28rdpobCU6Pe6q5bbG00", 
            type="secondary"
        )

    st.warning("🚨 **Important** : Si le commerçant ne répond pas à votre mise en demeure, vous devez faire un signalement officiel sur **SignalConso**.")
    st.link_button("Aller sur SignalConso.gouv.fr", "https://signal.conso.gouv.fr/", type="secondary")

    st.divider()

    col_res1, col_res2 = st.columns(2)

    with col_res1:
        st.subheader("📦 Achats en Ligne")
        with st.expander("Le Droit de Rétractation (14 jours)"):
            st.markdown("""
            **Article L221-18 du Code de la consommation**
            * Vous avez **14 jours** pour changer d'avis sans justification.
            * Le vendeur doit vous rembourser la totalité (y compris frais de livraison standard).
            * **Exception** : Produits personnalisés, périssables, ou logiciels descellés.
            """)
        
        with st.expander("Retard de Livraison"):
            st.markdown("""
            **Article L216-1**
            * Le vendeur doit livrer à la date indiquée.
            * Sans date, il a **30 jours maximum**.
            * Si retard : Vous pouvez annuler la commande par recommandé et exiger le remboursement.
            """)

    with col_res2:
        st.subheader("🛡️ Garanties")
        with st.expander("Garantie Légale de Conformité (2 ans)"):
            st.markdown("""
            **Durée : 2 ans** à compter de l'achat.
            * **Panne < 12 mois** (ou 24 mois pour le neuf) : C'est supposé être un défaut d'origine. C'est au vendeur de prouver le contraire.
            * Le vendeur doit **réparer** ou **remplacer** le produit sans frais.
            """)
        
        with st.expander("Garantie des Vices Cachés"):
            st.markdown("""
            Concerne un défaut **invisible** au moment de l'achat qui rend le produit inutilisable.
            * Vous pouvez demander le remboursement total (en rendant le produit) ou partiel (en le gardant).
            * Nécessite souvent une expertise.
            """)

    st.divider()
    st.info("💡 **Conseil Justibots** : Gardez toujours une trace écrite (Email ou Recommandé). Les appels téléphoniques n'ont aucune valeur juridique en cas de litige.")