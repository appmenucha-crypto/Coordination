"""
Configuration des URLs pour le projet
"""

from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from GestionDepartement.views import (
    departement,
    accueil, gestion, finance, communion, formation_view, communication,
    liste_membres, ajout_membre, profil_membre, modifier_membre, supprimer_membre,
    ajout_presence,
    soumission_rapport_culte,
    ajout_transaction, finance_departement,
    ajout_stagiaire, liste_stagiaires, supprimer_stagiaire, modifier_statut_stagiaire,
    ajout_evenement, liste_evenements, marquer_evenement_realise, marquer_evenement_prevu, export_evenements_pdf, supprimer_evenement,
    soumission_fiche_sante,
    liste_actualites, ajout_actualite, modifier_actualite, supprimer_actualite, ajout_media,
    liste_formations, ajout_formation, modifier_formation, supprimer_formation, valider_formation, rejeter_formation,
    liste_groupes, ajout_groupe, gestion_services, ajout_planning, gestion_membres_groupe, gestion_taches_planning, suivi_planning, supprimer_groupe, supprimer_planning,
    rapport_incident, liste_incidents, resoudre_incident,
    liste_commissions, ajout_commission, assigner_membre_commission,
    api_membres, api_statistiques, api_presences, api_responsable_departement,
    # Nouvelles vues
    connexion, deconnexion, inscription,
    dashboard_admin, dashboard_responsable,
    liste_notifications, marquer_notification_lue, marquer_toutes_notifications_lues,
    liste_activites, supprimer_activite, supprimer_toutes_activites,
    liste_rapports_culte, detail_rapport_culte, modifier_rapport_culte, supprimer_rapport_culte,
    transmission_resume_culte,
    # Nouvelles vues pour les responsables de départements
    liste_responsables, creer_responsable, modifier_responsable, supprimer_responsable, reinitialiser_mot_de_passe,
    # Vues commission Trésor Finance
    tresor_finance, ajout_impaye, payer_impaye, relancer_impaye, creer_budget, suivre_budget, liste_impayes,
    # Export PDF
    export_recapitulatif_pdf, export_finances_pdf,
    # Gestion du profil admin
    modifier_profil_admin,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', connexion, name='connexion'),
    
    
    # Pages principales
    path('accueil/', accueil, name='accueil'),
    path('departement/', departement, name='departement'),
    path('gestion/', gestion, name='gestion'),
    path('finance/', finance, name='finance'),
    path('finance/departement/', finance_departement, name='finance_departement'),
    path('communion/', communion, name='communion'),
    path('formation/', formation_view, name='formation'),
    path('communication/', communication, name='communication'),
    
    # Authentification
    path('connexion/', connexion, name='connexion'),
    path('deconnexion/', deconnexion, name='deconnexion'),
    path('inscription/', inscription, name='inscription'),
    
    
    # Dashboard Admin
    path('dashboard/', dashboard_admin, name='dashboard_admin'),
    path('dashboard/responsable/', dashboard_responsable, name='dashboard_responsable'),
    path('profil/', modifier_profil_admin, name='modifier_profil_admin'),
    
    # Notifications
    path('notifications/', liste_notifications, name='liste_notifications'),
    path('notifications/<int:notification_id>/lire/', marquer_notification_lue, name='marquer_notification_lue'),
    path('notifications/tout-lire/', marquer_toutes_notifications_lues, name='marquer_toutes_notifications_lues'),
    
    # Activités / Logs
    path('activites/', liste_activites, name='liste_activites'),
    path('activites/<int:activite_id>/supprimer/', supprimer_activite, name='supprimer_activite'),
    path('activites/supprimer-toutes/', supprimer_toutes_activites, name='supprimer_toutes_activites'),
    
    # Rapports
    path('rapports/culte/', liste_rapports_culte, name='liste_rapports_culte'),
    path('rapports/culte/<int:rapport_id>/', detail_rapport_culte, name='detail_rapport_culte'),
    path('rapports/culte/<int:rapport_id>/modifier/', modifier_rapport_culte, name='modifier_rapport_culte'),
    path('rapports/culte/<int:rapport_id>/supprimer/', supprimer_rapport_culte, name='supprimer_rapport_culte'),
    
    # Membres
    path('membres/', liste_membres, name='liste_membres'),
    path('membres/ajouter/', ajout_membre, name='ajout_membre'),
    path('membres/<int:membre_id>/', profil_membre, name='profil_membre'),
    path('membres/<int:membre_id>/modifier/', modifier_membre, name='modifier_membre'),
    path('membres/<int:membre_id>/supprimer/', supprimer_membre, name='supprimer_membre'),
    
    # Présences
    path('presences/ajouter/', ajout_presence, name='ajout_presence'),
    
    # Rapports de culte
    path('rapport/culte/', soumission_rapport_culte, name='soumission_rapport_culte'),
    path('transmission/resume/', transmission_resume_culte, name='transmission_resume_culte'),
    
    # Transactions
    path('transactions/ajouter/', ajout_transaction, name='ajout_transaction'),
    
    # Stagiaires
    path('stagiaires/ajouter/', ajout_stagiaire, name='ajout_stagiaire'),
    path('stagiaires/', liste_stagiaires, name='liste_stagiaires'),
    path('stagiaires/<int:stagiaire_id>/supprimer/', supprimer_stagiaire, name='supprimer_stagiaire'),
    path('stagiaires/<int:stagiaire_id>/modifier-statut/', modifier_statut_stagiaire, name='modifier_statut_stagiaire'),
    
    # Evénements
    path('evenements/ajouter/', ajout_evenement, name='ajout_evenement'),
    path('evenements/', liste_evenements, name='liste_evenements'),
    path('evenements/<int:evenement_id>/realise/', marquer_evenement_realise, name='marquer_evenement_realise'),
    path('evenements/<int:evenement_id>/prevu/', marquer_evenement_prevu, name='marquer_evenement_prevu'),
    path('evenements/<int:evenement_id>/supprimer/', supprimer_evenement, name='supprimer_evenement'),
    path('evenements/export-pdf/', export_evenements_pdf, name='export_evenements_pdf'),
    
    # Fiche santé spirituelle
    path('sante-spirituelle/', soumission_fiche_sante, name='soumission_fiche_sante'),
    
    # Actualités
    path('actualites/', liste_actualites, name='liste_actualites'),
    path('actualites/ajouter/', ajout_actualite, name='ajout_actualite'),
    path('actualites/<int:actualite_id>/modifier/', modifier_actualite, name='modifier_actualite'),
    path('actualites/<int:actualite_id>/supprimer/', supprimer_actualite, name='supprimer_actualite'),
    
    # Médias (galerie)
    path('medias/ajouter/', ajout_media, name='ajout_media'),
    
    # Formations
    path('formations/', liste_formations, name='liste_formations'),
    path('formations/ajouter/', ajout_formation, name='ajout_formation'),
    path('formations/<int:formation_id>/modifier/', modifier_formation, name='modifier_formation'),
    path('formations/<int:formation_id>/supprimer/', supprimer_formation, name='supprimer_formation'),
    path('formations/<int:formation_id>/valider/', valider_formation, name='valider_formation'),
    path('formations/<int:formation_id>/rejeter/', rejeter_formation, name='rejeter_formation'),
    
    # Groupes de service
    path('groupes/', liste_groupes, name='liste_groupes'),
    path('groupes/ajouter/', ajout_groupe, name='ajout_groupe'),
    path('groupes/<int:groupe_id>/membres/', gestion_membres_groupe, name='gestion_membres_groupe'),
    path('groupes/<int:groupe_id>/supprimer/', supprimer_groupe, name='supprimer_groupe'),
    path('gestion-services/', gestion_services, name='gestion_services'),
    path('planning/ajouter/', ajout_planning, name='ajout_planning'),
    path('planning/<int:planning_id>/taches/', gestion_taches_planning, name='gestion_taches_planning'),
    path('planning/<int:planning_id>/suivi/', suivi_planning, name='suivi_planning'),
    path('planning/<int:planning_id>/supprimer/', supprimer_planning, name='supprimer_planning'),
    
    # Incidents
    path('incidents/rapporter/', rapport_incident, name='rapport_incident'),
    path('incidents/', liste_incidents, name='liste_incidents'),
    path('incidents/<int:incident_id>/resoudre/', resoudre_incident, name='resoudre_incident'),
    
    # Commissions
    path('commissions/', liste_commissions, name='liste_commissions'),
    path('commissions/ajouter/', ajout_commission, name='ajout_commission'),
    path('commissions/assigner/', assigner_membre_commission, name='assigner_membre_commission'),
    
    # API
    path('api/membres/', api_membres, name='api_membres'),
    path('api/statistiques/', api_statistiques, name='api_statistiques'),
    path('api/presences/', api_presences, name='api_presences'),
    path('api/responsable-departement/', api_responsable_departement, name='api_responsable_departement'),
    
    # Responsables de départements
    path('responsables/', liste_responsables, name='liste_responsables'),
    path('responsables/creer/', creer_responsable, name='creer_responsable'),
    path('responsables/<int:departement_id>/modifier/', modifier_responsable, name='modifier_responsable'),
    path('responsables/<int:departement_id>/supprimer/', supprimer_responsable, name='supprimer_responsable'),
    path('responsables/<int:departement_id>/reinitialiser-mot-de-passe/', reinitialiser_mot_de_passe, name='reinitialiser_mot_de_passe'),
    
    # Commission Trésor Finance
    path('tresor-finance/', tresor_finance, name='tresor_finance'),
    path('tresor-finance/impayes/ajouter/', ajout_impaye, name='ajout_impaye'),
    path('tresor-finance/impayes/<int:impaye_id>/payer/', payer_impaye, name='payer_impaye'),
    path('tresor-finance/impayes/<int:impaye_id>/relancer/', relancer_impaye, name='relancer_impaye'),
    path('tresor-finance/impayes/', liste_impayes, name='liste_impayes'),
    path('tresor-finance/budget/creer/', creer_budget, name='creer_budget'),
    path('tresor-finance/budget/', suivre_budget, name='suivre_budget'),
    
    # Export PDF
    path('export-recapitulatif-pdf/', export_recapitulatif_pdf, name='export_recapitulatif_pdf'),
    path('export-finances-pdf/', export_finances_pdf, name='export_finances_pdf'),
]

# Configuration pour servir les fichiers médias (Images, Vidéos)
# Cette méthode force Django à servir les fichiers médias même en production
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]
