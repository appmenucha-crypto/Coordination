"""
Vues Django pour la gestion des départements
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator

from .models import (
    Membre, Presence, RapportCulte, TransmissionResume, Stagiaire,
    Evenement, Transaction, FicheSanteSpirituelle, GroupeService,
    PlanningService, Formation, Actualite, Message, Incident, Commission,
    UserProfile, Notification, ActiviteLog, Departement, Impayes, Budget
)
from .utils import generer_pdf_recapitulatif


@login_required
def departement(request):
    """Vue principale affichant le tableau de bord"""
    
    # Statistiques générales
    total_membres = Membre.objects.count()
    membres_actifs = Membre.objects.filter(status=Membre.Status.ACTIF).count()
    sentinelles = Membre.objects.filter(est_sentinelle=True).count()
    
    # Statistiques financières
    total_entrees = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    total_sorties = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    solde = total_entrees - total_sorties
    
    # Statistiques des présences
    presences_recentes = Presence.objects.filter(
        date__gte=timezone.now().date() - timedelta(days=7)
    ).count()
    
    absences_recentes = Presence.objects.filter(
        date__gte=timezone.now().date() - timedelta(days=7),
        status=Presence.StatusPresence.ABSENT
    ).count()
    
    # Evenements à venir
    evenements_a_venir = Evenement.objects.filter(
        date_evenement__gte=timezone.now().date(),
        statut=Evenement.StatutEvenement.PREVU
    ).order_by('date_evenement')[:5]
    
    # Dernières actualités
    dernieres_actualites = Actualite.objects.filter(
        est_publie=True
    ).order_by('-date_publication')[:3]
    
    # Stagiaires en cours
    stagiaires = Stagiaire.objects.filter(
        statut=Stagiaire.StatutStage.EN_COURS
    )
    
    # Groupes de service
    groupes = GroupeService.objects.filter(est_actif=True)
    
    # Transactions récentes
    transactions_recents = Transaction.objects.order_by('-date_transaction')[:5]
    
    # Commissions
    commissions = Commission.objects.filter(est_active=True)
    
    # Liste des membres pour les formulaires
    membres = Membre.objects.all().order_by('nom', 'prenom')
    
    context = {
        'total_membres': total_membres,
        'membres_actifs': membres_actifs,
        'sentinelles': sentinelles,
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'solde': solde,
        'presences_recentes': presences_recentes,
        'absences_recentes': absences_recentes,
        'evenements_a_venir': evenements_a_venir,
        'dernieres_actualites': dernieres_actualites,
        'stagiaires': stagiaires,
        'groupes': groupes,
        'transactions_recents': transactions_recents,
        'commissions': commissions,
        'membres': membres,
    }
    
    return render(request, 'departement.html', context)


@login_required
def accueil(request):
    """Vue d'accueil - page d'accueil principale"""
    
    # Statistiques générales
    total_membres = Membre.objects.count()
    membres_actifs = Membre.objects.filter(status=Membre.Status.ACTIF).count()
    sentinelles = Membre.objects.filter(est_sentinelle=True).count()
    
    # Statistiques financières
    total_entrees = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    total_sorties = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    solde = total_entrees - total_sorties
    
    # Evénements à venir
    evenements_a_venir = Evenement.objects.filter(
        date_evenement__gte=timezone.now().date(),
        statut=Evenement.StatutEvenement.PREVU
    ).order_by('date_evenement')[:5]
    
    # Dernières actualités
    dernieres_actualites = Actualite.objects.filter(
        est_publie=True
    ).order_by('-date_publication')[:3]
    
    # Stagiaires en cours
    stagaires = Stagiaire.objects.filter(
        statut=Stagiaire.StatutStage.EN_COURS
    )
    
    # Groupes de service
    groupes = GroupeService.objects.filter(est_actif=True)
    
    # Transactions récentes
    transactions_recents = Transaction.objects.order_by('-date_transaction')[:5]
    
    # Commissions
    commissions = Commission.objects.filter(est_active=True)
    
    # Formations
    formations = Formation.objects.all().order_by('-date_debut')[:6]
    
    # Liste des membres pour les formulaires
    membres = Membre.objects.all().order_by('nom', 'prenom')
    
    context = {
        'total_membres': total_membres,
        'membres_actifs': membres_actifs,
        'sentinelles': sentinelles,
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'solde': solde,
        'evenements_a_venir': evenements_a_venir,
        'dernieres_actualites': dernieres_actualites,
        'stagiaires': stagaires,
        'groupes': groupes,
        'transactions_recents': transactions_recents,
        'commissions': commissions,
        'formations': formations,
        'membres': membres,
    }
    
    return render(request, 'accueil.html', context)


@login_required
def gestion(request):
    """Vue pour la gestion des rapports et discipline"""
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    # Vérifier si l'utilisateur est un responsable ou admin
    is_responsable = False
    is_admin = False
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.role == UserProfile.Role.RESPONSABLE:
                is_responsable = True
            elif profile.role == UserProfile.Role.ADMIN:
                is_admin = True
        except UserProfile.DoesNotExist:
            pass
    
    # Filtrer les membres : admin voit tout, responsable voit son département
    if is_admin:
        membres = Membre.objects.all().order_by('nom', 'prenom')
    elif is_responsable and nom_departement:
        membres = Membre.objects.filter(departement=nom_departement).order_by('nom', 'prenom')
    else:
        membres = Membre.objects.all().order_by('nom', 'prenom')
    
    context = {
        'membres': membres,
        'nom_departement': nom_departement,
        'is_responsable': is_responsable,
        'is_admin': is_admin,
    }
    
    return render(request, 'gestion.html', context)


@login_required
def finance(request):
    """Vue pour la trésorerie et les finances - Réservé aux administrateurs"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    # Statistiques financières globales
    total_entrees = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    total_sorties = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    solde = total_entrees - total_sorties
    
    # Soldes par département
    from django.db.models import Q
    departements_list = Membre.Departement.choices
    soldes_departements = []
    
    for dept_code, dept_nom in departements_list:
        entrees_dept = Transaction.objects.filter(
            departement=dept_code,
            type_mouvement=Transaction.TypeMouvement.ENTREE
        ).aggregate(Sum('montant'))['montant__sum'] or 0
        
        sorties_dept = Transaction.objects.filter(
            departement=dept_code,
            type_mouvement=Transaction.TypeMouvement.SORTIE
        ).aggregate(Sum('montant'))['montant__sum'] or 0
        
        solde_dept = entrees_dept - sorties_dept
        
        soldes_departements.append({
            'code': dept_code,
            'nom': dept_nom,
            'entrees': entrees_dept,
            'sorties': sorties_dept,
            'solde': solde_dept
        })
    
    # Transactions récentes (toutes pour permettre le filtrage)
    transactions_recents = Transaction.objects.select_related('membre').order_by('-date_transaction')[:50]
    
    context = {
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'solde': solde,
        'soldes_departements': soldes_departements,
        'transactions_recents': transactions_recents,
        'departements_list': departements_list,
    }
    
    return render(request, 'admin/finance.html', context)


@login_required
def finance_departement(request):
    """Vue pour la gestion financière d'un département (Responsables)"""
    # Vérifier si l'utilisateur est un responsable
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.RESPONSABLE:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('dashboard_admin')
    
    # Récupérer le département du responsable
    nom_departement = get_departement_for_user(request.user)
    
    if not nom_departement:
        messages.error(request, 'Aucun département associé à votre compte.')
        return redirect('dashboard_responsable')
    
    # Filtrer les transactions par le champ departement (créées par l'admin)
    transactions = Transaction.objects.filter(
        departement=nom_departement
    ).order_by('-date_transaction')
    
    # Statistiques
    total_entrees = transactions.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    total_sorties = transactions.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    solde = total_entrees - total_sorties
    
    # Transactions récentes
    transactions_recents = transactions[:50]
    
    # Membres du département
    membres_departement = Membre.objects.filter(departement=nom_departement).order_by('nom', 'prenom')
    
    context = {
        'nom_departement': nom_departement,
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'solde': solde,
        'transactions_recents': transactions_recents,
        'membres': membres_departement,
    }
    
    return render(request, 'responsable/finance.html', context)


@login_required
def communion(request):
    """Vue pour la communion fraternelle et l'intégration"""
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    # Vérifier si l'utilisateur est un responsable ou admin
    is_responsable = False
    is_admin = False
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.role == UserProfile.Role.RESPONSABLE:
                is_responsable = True
            elif profile.role == UserProfile.Role.ADMIN:
                is_admin = True
        except UserProfile.DoesNotExist:
            pass
    
    # Stagiaires : admin voit tout, responsable voit son département
    if is_admin:
        stagaires = Stagiaire.objects.all().order_by('-date_debut')
    elif is_responsable and nom_departement:
        stagaires = Stagiaire.objects.filter(
            departement_accueil=nom_departement
        ).order_by('-date_debut')
    else:
        stagaires = Stagiaire.objects.all().order_by('-date_debut')
    
    # Evénements à venir : admin voit tout, responsable voit son département
    if is_admin:
        evenements_a_venir = Evenement.objects.filter(
            date_evenement__gte=timezone.now().date(),
            statut=Evenement.StatutEvenement.PREVU
        ).order_by('date_evenement')[:5]
    elif is_responsable and nom_departement:
        evenements_a_venir = Evenement.objects.filter(
            date_evenement__gte=timezone.now().date(),
            statut=Evenement.StatutEvenement.PREVU,
            responsable__departement=nom_departement
        ).order_by('date_evenement')[:5]
    else:
        evenements_a_venir = Evenement.objects.filter(
            date_evenement__gte=timezone.now().date(),
            statut=Evenement.StatutEvenement.PREVU
        ).order_by('date_evenement')[:5]
    
    # Commissions actives
    commissions = Commission.objects.filter(est_active=True).order_by('nom')
    
    # Liste des membres : admin voit tout, responsable voit son département
    if is_admin:
        membres = Membre.objects.all().order_by('nom', 'prenom')
    elif is_responsable and nom_departement:
        membres = Membre.objects.filter(departement=nom_departement).order_by('nom', 'prenom')
    else:
        membres = Membre.objects.all().order_by('nom', 'prenom')
    
    context = {
        'stagaires': stagaires,
        'evenements_a_venir': evenements_a_venir,
        'commissions': commissions,
        'membres': membres,
        'nom_departement': nom_departement,
        'is_responsable': is_responsable,
        'is_admin': is_admin,
    }
    
    return render(request, 'communion.html', context)


@login_required
def formation_view(request):
    """Vue pour les formations techniques - Commission Formation"""
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    # Vérifier si l'utilisateur est un responsable ou admin
    is_responsable = False
    is_admin = False
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.role == UserProfile.Role.RESPONSABLE:
                is_responsable = True
            elif profile.role == UserProfile.Role.ADMIN:
                is_admin = True
        except UserProfile.DoesNotExist:
            pass
    
    # Filtrer les formations
    if is_admin:
        # Admin voit toutes les formations
        formations = Formation.objects.all().order_by('-date_debut')
    elif nom_departement:
        # Responsable voit les formations pour son département OU pour tous (departement vide)
        formations = Formation.objects.filter(
            Q(departement=nom_departement) | Q(departement='')
        ).order_by('-date_debut')
    else:
        formations = Formation.objects.filter(departement='').order_by('-date_debut')
    
    context = {
        'nom_departement': nom_departement,
        'formations': formations,
        'is_responsable': is_responsable,
        'is_admin': is_admin,
    }
    
    return render(request, 'formation.html', context)


@login_required
def communication(request):
    """Vue pour la communication et les médias"""
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    # Dernières actualités
    dernieres_actualites = Actualite.objects.filter(
        est_publie=True
    ).order_by('-date_publication')
    
    # Médias de la galerie (photos et vidéos)
    from .models import MediaGalerie
    galerie_medias = MediaGalerie.objects.all().order_by('-date_ajout')[:12]
    
    context = {
        'nom_departement': nom_departement,
        'dernieres_actualites': dernieres_actualites,
        'galerie_medias': galerie_medias,
    }
    
    return render(request, 'communication.html', context)


@login_required
def ajout_media(request):
    """Ajout d'un média (photo ou vidéo) dans la galerie"""
    if request.method == 'POST':
        try:
            from .models import MediaGalerie
            media = MediaGalerie(
                titre=request.POST.get('titre'),
                type_media=request.POST.get('type_media', 'image'),
                description=request.POST.get('description', ''),
            )
            
            # Gérer l'upload du fichier
            if request.FILES.get('fichier'):
                media.fichier = request.FILES.get('fichier')
            
            media.save()
            messages.success(request, 'Média ajouté avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('communication')


# ==================== MEMBRE VIEWS ====================

@login_required
def liste_membres(request):
    """Liste de tous les membres - Filtrée par département pour les responsables"""
    # Vérifier le rôle de l'utilisateur
    nom_departement = None
    is_admin = False
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.ADMIN:
            # Admin voit tous les membres
            membres = Membre.objects.all().order_by('nom', 'prenom')
            is_admin = True
        elif profile.role == UserProfile.Role.RESPONSABLE:
            # Responsable voit uniquement les membres de son département
            nom_departement = get_departement_for_user(request.user)
            if nom_departement:
                membres = Membre.objects.filter(departement=nom_departement).order_by('nom', 'prenom')
            else:
                membres = Membre.objects.none()
        else:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    template = 'admin/liste_membres.html' if is_admin else 'responsable/liste_membres.html'
    return render(request, template, {'membres': membres, 'nom_departement': nom_departement})


@login_required
def ajout_membre(request):
    """Ajout d'un nouveau membre"""
    is_admin = False
    nom_departement = None
    
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.ADMIN:
            is_admin = True
        else:
            nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    except UserProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        try:
            # Récupérer le département du responsable connecté
            if not is_admin:
                nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
            
            membre = Membre(
                nom=request.POST.get('nom'),
                prenom=request.POST.get('prenom'),
                email=request.POST.get('email'),
                telephone=request.POST.get('telephone'),
                adresse=request.POST.get('adresse'),
                role=request.POST.get('role', 'MEMBRE'),
                status=request.POST.get('status', 'ACTIF'),
                est_sentinelle=request.POST.get('est_sentinelle') == 'on',
                groupe_sentinelle=request.POST.get('groupe_sentinelle', ''),
                departement=nom_departement or request.POST.get('departement', ''),
                est_responsable=request.POST.get('est_responsable') == 'on',
            )
            membre.save()
            messages.success(request, 'Membre ajouté avec succès!')
            return redirect('liste_membres')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    # Handle GET request - render the form
    template = 'admin/ajout_membre.html' if is_admin else 'responsable/ajout_membre.html'
    return render(request, template, {'nom_departement': nom_departement})


# ==================== PRESENCE VIEWS ====================

@login_required
def ajout_presence(request):
    """Enregistrement d'une présence"""
    if request.method == 'POST':
        try:
            membre_id = request.POST.get('membre')
            membre = get_object_or_404(Membre, id=membre_id)
            
            presence = Presence(
                membre=membre,
                date=request.POST.get('date'),
                type_activite=request.POST.get('type_activite'),
                status=request.POST.get('status'),
                motif_absence=request.POST.get('motif_absence', ''),
            )
            presence.save()
            messages.success(request, 'Présence enregistrée!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('gestion')


# ==================== RAPPORT CULTE VIEWS ====================

@login_required
def soumission_rapport_culte(request):
    """Soumission d'un rapport de culte et transmission des résumés"""
    if request.method == 'POST':
        try:
            # Créer le rapport de culte
            rapport = RapportCulte(
                responsable_id=request.POST.get('responsable'),
                nom_departement=request.POST.get('nom_departement', ''),
                date_culte=request.POST.get('date_culte'),
                statut=RapportCulte.Statut.SOUMIS,
                
                # Prière 1er culte
                priere_1_nbre=request.POST.get('priere_1_nbre', 0),
                priere_1_programme=request.POST.get('priere_1_programme', 0),
                priere_1_absent=request.POST.get('priere_1_absent', 0),
                priere_1_motifs=request.POST.get('priere_1_motifs', ''),
                
                # 1er Culte
                culte_1_nbre=request.POST.get('culte_1_nbre', 0),
                culte_1_programme=request.POST.get('culte_1_programme', 0),
                culte_1_absent=request.POST.get('culte_1_absent', 0),
                culte_1_motifs=request.POST.get('culte_1_motifs', ''),
                
                # Prière 2ème culte
                priere_2_nbre=request.POST.get('priere_2_nbre', 0),
                priere_2_programme=request.POST.get('priere_2_programme', 0),
                priere_2_absent=request.POST.get('priere_2_absent', 0),
                priere_2_motifs=request.POST.get('priere_2_motifs', ''),
                
                # 2ème Culte
                culte_2_nbre=request.POST.get('culte_2_nbre', 0),
                culte_2_programme=request.POST.get('culte_2_programme', 0),
                culte_2_absent=request.POST.get('culte_2_absent', 0),
                culte_2_motifs=request.POST.get('culte_2_motifs', ''),
                
                # Culte des Boss
                culte_boss_nbre=request.POST.get('culte_boss_nbre', 0),
                culte_boss_programme=request.POST.get('culte_boss_programme', 0),
                culte_boss_absent=request.POST.get('culte_boss_absent', 0),
                culte_boss_motifs=request.POST.get('culte_boss_motifs', ''),
                
                # Réveil Sentinelles
                reveil_sentinelles_nbre=request.POST.get('reveil_sentinelles_nbre', 0),
                reveil_sentinelles_programme=request.POST.get('reveil_sentinelles_programme', 0),
                reveil_sentinelles_absent=request.POST.get('reveil_sentinelles_absent', 0),
                reveil_sentinelles_motifs=request.POST.get('reveil_sentinelles_motifs', ''),
                
                # Observations
                points_forts=request.POST.get('points_forts', ''),
                difficultes=request.POST.get('difficultes', ''),
                recommandations=request.POST.get('recommandations', ''),
            )
            rapport.save()
            
            # Traiter les transmissions de résumés (nouveaux champs simples)
            date_culte = request.POST.get('date_culte')
            transmission_culte_1 = int(request.POST.get('transmission_culte_1', 0))
            transmission_culte_2 = int(request.POST.get('transmission_culte_2', 0))
            transmission_culte_boss = int(request.POST.get('transmission_culte_boss', 0))
            
            # Créer des transmissions pour 1er Culte
            for i in range(transmission_culte_1):
                TransmissionResume.objects.create(
                    serviteur_id=request.POST.get('responsable'),
                    culte='1er Culte',
                    date_culte=date_culte,
                    statut=TransmissionResume.StatutTransmission.TRANSMIS,
                    respect_delai=True,
                    observation=f'Résumé {i+1}'
                )
            
            # Créer des transmissions pour 2ème Culte
            for i in range(transmission_culte_2):
                TransmissionResume.objects.create(
                    serviteur_id=request.POST.get('responsable'),
                    culte='2ème Culte',
                    date_culte=date_culte,
                    statut=TransmissionResume.StatutTransmission.TRANSMIS,
                    respect_delai=True,
                    observation=f'Résumé {i+1}'
                )
            
            # Créer des transmissions pour Culte des Boss
            for i in range(transmission_culte_boss):
                TransmissionResume.objects.create(
                    serviteur_id=request.POST.get('responsable'),
                    culte='Culte des Boss',
                    date_culte=date_culte,
                    statut=TransmissionResume.StatutTransmission.TRANSMIS,
                    respect_delai=True,
                    observation=f'Résumé {i+1}'
                )
            
            # Traiter les transmissions de résumés (anciens champs détaillés)
            count = 3
            for i in range(1, count + 1):
                serviteur_id = request.POST.get(f'serviteur_{i}')
                culte = request.POST.get(f'culte_{i}')
                date_culte_trans = request.POST.get(f'date_culte_{i}')
                resume_transmis = request.POST.get(f'resum_transmis_{i}')
                date_transmission = request.POST.get(f'date_transmission_{i}')
                respect_delai = request.POST.get(f'respect_delai_{i}')
                observation = request.POST.get(f'observation_{i}')

                if serviteur_id and culte:
                    if resume_transmis == 'Oui':
                        statut = TransmissionResume.StatutTransmission.TRANSMIS
                    elif resume_transmis == 'En retard':
                        statut = TransmissionResume.StatutTransmission.EN_RETARD
                    else:
                        statut = TransmissionResume.StatutTransmission.NON_TRANSMIS

                    TransmissionResume.objects.create(
                        serviteur_id=serviteur_id,
                        culte=culte,
                        date_culte=date_culte_trans if date_culte_trans else request.POST.get('date_culte'),
                        date_transmission=date_transmission if date_transmission else None,
                        statut=statut,
                        respect_delai=respect_delai == 'Oui',
                        observation=observation or ''
                    )
            
            messages.success(request, 'Rapport de culte et transmissions enregistrés avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('gestion')


# ==================== TRANSACTION VIEWS ====================

@login_required
def ajout_transaction(request):
    """Ajout d'une transaction financière"""
    if request.method == 'POST':
        try:
            transaction = Transaction(
                type_transaction=request.POST.get('type_transaction'),
                type_mouvement=request.POST.get('type_mouvement'),
                montant=request.POST.get('montant'),
                description=request.POST.get('description'),
                justification=request.POST.get('justification', ''),
                categorie=request.POST.get('categorie', 'AUTRE'),
                departement=request.POST.get('departement', ''),
            )
            
            # Si c'est une entrée, associate with member
            membre_id = request.POST.get('membre')
            if membre_id:
                transaction.membre_id = membre_id
            
            transaction.save()
            messages.success(request, 'Transaction enregistrée avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    # Redirection selon le rôle
    if request.user.is_authenticated:
        try:
            if request.user.profile.role == UserProfile.Role.RESPONSABLE:
                return redirect('finance_departement')
            elif request.user.profile.role == UserProfile.Role.ADMIN:
                return redirect('finance')
        except:
            pass
            
    return redirect('finance')


# ==================== STAGIAIRE VIEWS ====================

@login_required
def ajout_stagiaire(request):
    """Ajout d'un nouveau stagiaire"""
    if request.method == 'POST':
        try:
            # Récupérer le département du responsable connecté
            nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
            
            stagiaire = Stagiaire(
                nom=request.POST.get('nom'),
                prenom=request.POST.get('prenom'),
                email=request.POST.get('email'),
                telephone=request.POST.get('telephone'),
                date_naissance=request.POST.get('date_naissance'),
                date_debut=request.POST.get('date_debut'),
                departement_accueil=nom_departement,  # Utiliser automatiquement le département du responsable
                statut=Stagiaire.StatutStage.EN_COURS,  # Définir explicitement le statut
                taches_assignees=request.POST.get('taches_assignees', ''),
            )
            
            tuteur_id = request.POST.get('tuteur')
            if tuteur_id:
                stagiaire.tuteur_id = tuteur_id
            
            stagiaire.save()
            messages.success(request, 'Stagiaire ajouté avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('communion')


# ==================== EVENEMENT VIEWS ====================

@login_required
def ajout_evenement(request):
    """Ajout d'un nouvel événement"""
    if request.method == 'POST':
        try:
            # Récupérer le département du responsable connecté
            nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else ''
            
            evenement = Evenement(
                type_evenement=request.POST.get('type_evenement'),
                titre=request.POST.get('titre'),
                description=request.POST.get('description', ''),
                date_evenement=request.POST.get('date_evenement'),
                lieu=request.POST.get('lieu', ''),
                heure=request.POST.get('heure'),
                montant_collecte=request.POST.get('montant_collecte', 0),
                montant_depense=request.POST.get('montant_depense', 0),
            )
            
            # Assigner automatiquement le responsable connecté comme responsable de l'événement
            if request.user.is_authenticated:
                try:
                    profile = request.user.profile
                    if profile.membre:
                        evenement.responsable = profile.membre
                except:
                    pass
            
            responsable_id = request.POST.get('responsable')
            if responsable_id:
                evenement.responsable_id = responsable_id
            
            evenement.save()
            messages.success(request, 'Événement créé avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('communion')


# ==================== FICHE SANTE SPIRITUELLE VIEWS ====================

@login_required
def soumission_fiche_sante(request):
    """Soumission d'une fiche de santé spirituelle"""
    if request.method == 'POST':
        try:
            fiche = FicheSanteSpirituelle(
                membre_id=request.POST.get('membre'),
                mois=request.POST.get('mois'),
                priere_quotidienne=request.POST.get('priere_quotidienne'),
                lecture_biblique=request.POST.get('lecture_biblique'),
                communion_avec_dieu=request.POST.get('communion_avec_dieu'),
                assiduite_culte=request.POST.get('assiduite_culte'),
                service_rendu=request.POST.get('service_rendu'),
                defis_spirituels=request.POST.get('defis_spirituels', ''),
                objectifs_suivant_mois=request.POST.get('objectifs_suivant_mois', ''),
                besoins_specifiques=request.POST.get('besoins_specifiques', ''),
                prieres=request.POST.get('prieres', ''),
            )
            fiche.save()
            messages.success(request, 'Fiche de santé spirituelle enregistrée!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('gestion')


# ==================== ACTUALITE VIEWS ====================

@login_required
def liste_actualites(request):
    """Liste des actualités"""
    actualites = Actualite.objects.filter(est_publie=True).order_by('-date_publication')
    return render(request, 'actualites/liste.html', {'actualites': actualites})


@login_required
def ajout_actualite(request):
    """Ajout d'une actualité"""
    if request.method == 'POST':
        try:
            actualite = Actualite(
                titre=request.POST.get('titre'),
                contenu=request.POST.get('contenu'),
                categorie=request.POST.get('categorie', 'AUTRE'),
                est_urgent=request.POST.get('est_urgent') == 'on',
            )

            # Gérer l'upload de l'image
            if request.FILES.get('image'):
                actualite.image = request.FILES.get('image')

            auteur_id = request.POST.get('auteur')
            if auteur_id:
                actualite.auteur_id = auteur_id

            actualite.save()
            messages.success(request, 'Actualité publiée avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')

    return redirect('communication')


@login_required
def modifier_actualite(request, actualite_id):
    """Modifier une actualité"""
    actualite = get_object_or_404(Actualite, id=actualite_id)
    
    if request.method == 'POST':
        try:
            actualite.titre = request.POST.get('titre')
            actualite.contenu = request.POST.get('contenu')
            actualite.categorie = request.POST.get('categorie', 'AUTRE')
            actualite.est_urgent = request.POST.get('est_urgent') == 'on'
            
            # Gérer l'upload de la nouvelle image
            if request.FILES.get('image'):
                actualite.image = request.FILES.get('image')
            
            actualite.save()
            messages.success(request, 'Actualité modifiée avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
        
        return redirect('communication')
    
    # GET request - render the edit form
    return render(request, 'actualites/modifier.html', {'actualite': actualite})


@login_required
def supprimer_actualite(request, actualite_id):
    """Supprimer une actualité"""
    actualite = get_object_or_404(Actualite, id=actualite_id)
    
    if request.method == 'POST':
        try:
            actualite.delete()
            messages.success(request, 'Actualité supprimée avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('communication')


# ==================== FORMATION VIEWS ====================

@login_required
def liste_formations(request):
    """Liste des formations"""
    formations = Formation.objects.all().order_by('-date_debut')
    
    # Vérifier si l'utilisateur est admin
    is_admin = False
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            is_admin = profile.role == UserProfile.Role.ADMIN
        except UserProfile.DoesNotExist:
            pass
    
    return render(request, 'formations/liste.html', {
        'formations': formations,
        'is_admin': is_admin
    })


@login_required
def ajout_formation(request):
    """Ajout d'une formation"""
    if request.method == 'POST':
        try:
            # Vérifier si c'est un admin
            is_admin = False
            try:
                profile = request.user.profile
                is_admin = profile.role == UserProfile.Role.ADMIN
            except UserProfile.DoesNotExist:
                pass
            
            # Si admin, peut choisir le département destinataire, sinon utilise son propre département
            if is_admin:
                departement_dest = request.POST.get('departement_destinataire', '')
            else:
                departement_dest = get_departement_for_user(request.user) if request.user.is_authenticated else ''
            
            formation = Formation(
                titre=request.POST.get('titre'),
                description=request.POST.get('description'),
                date_debut=request.POST.get('date_debut'),
                date_fin=request.POST.get('date_fin'),
                lieu=request.POST.get('lieu', ''),
                est_en_ligne=request.POST.get('est_en_ligne') == 'on',
                lien_online=request.POST.get('lien_online', ''),
                departement=departement_dest,
                statut_validation=Formation.StatutValidation.VALIDEE if is_admin else Formation.StatutValidation.EN_ATTENTE,
            )
            
            # Gérer les uploads
            if request.FILES.get('supports'):
                formation.supports = request.FILES.get('supports')
            if request.FILES.get('video'):
                formation.video = request.FILES.get('video')
            if request.FILES.get('image'):
                formation.image = request.FILES.get('image')
            
            formation.save()
            
            if is_admin:
                messages.success(request, 'Formation créée et validée avec succès!')
                return redirect('liste_formations')
            else:
                messages.success(request, 'Formation créée avec succès! En attente de validation par l\'admin.')
                return redirect('formation')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('formation')


# ==================== GROUPE SERVICE VIEWS ====================

@login_required
def liste_groupes(request):
    """Liste des groupes de service"""
    groupes = GroupeService.objects.filter(est_actif=True)
    return render(request, 'groupes/liste.html', {'groupes': groupes})


@login_required
def gestion_services(request):
    """Page dédiée pour la gestion des services (rotation) - 7ème commission"""
    from django.db.models import Q, Count
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    # Vérifier si c'est un admin
    is_admin = False
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.ADMIN:
            is_admin = True
    except UserProfile.DoesNotExist:
        pass
    
    # Filtrer les membres et groupes par département
    if nom_departement and not is_admin:
        membres = Membre.objects.filter(departement=nom_departement)
        groupes = GroupeService.objects.filter(departement=nom_departement).order_by('nom_groupe')
    else:
        membres = Membre.objects.all()
        groupes = GroupeService.objects.all().order_by('nom_groupe')
    
    # Planning des services (filtrer par groupes du département)
    plannings = PlanningService.objects.filter(
        groupe__in=groupes,
        date_service__gte=timezone.now().date()
    ).order_by('date_service')[:10]
    
    # Statistiques
    total_membres = membres.count()
    groupes_actifs = groupes.filter(est_actif=True).count()
    
    context = {
        'nom_departement': nom_departement,
        'groupes': groupes,
        'plannings': plannings,
        'total_membres': total_membres,
        'groupes_actifs': groupes_actifs,
        'membres': membres,
    }
    
    return render(request, 'gestion_services.html', context)


@login_required
def ajout_groupe(request):
    """Ajout d'un groupe de service"""
    if request.method == 'POST':
        try:
            # Récupérer le département du responsable connecté
            nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else ''
            
            groupe = GroupeService(
                nom_groupe=request.POST.get('nom_groupe'),
                couleur=request.POST.get('couleur', '#FFD700'),
                description=request.POST.get('description', ''),
                jour_service=request.POST.get('jour_service', ''),
                departement=nom_departement,
            )
            groupe.save()
            messages.success(request, 'Groupe de service créé avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('gestion_services')


@login_required
def ajout_planning(request):
    """Ajout d'un planning de service"""
    if request.method == 'POST':
        try:
            groupe_id = request.POST.get('groupe')
            groupe = GroupeService.objects.get(id=groupe_id)
            
            # Créer le planning
            planning = PlanningService(
                date_service=request.POST.get('date_service'),
                type_service=request.POST.get('type_service'),
                groupe=groupe,
                notes=request.POST.get('notes', ''),
            )
            
            # Ajouter les tâches saisies manuellement
            taches_text = request.POST.get('taches', '')
            if taches_text:
                taches = [t.strip() for t in taches_text.split('\n') if t.strip()]
                planning.assignations = {tache: [] for tache in taches}
            
            planning.save()
            messages.success(request, 'Planning créé avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('formation')


@login_required
def gestion_membres_groupe(request, groupe_id):
    """Gérer les membres d'un groupe"""
    groupe = GroupeService.objects.get(id=groupe_id)
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    # Si le groupe n'a pas de département, l'assigner automatiquement
    if not groupe.departement and nom_departement:
        groupe.departement = nom_departement
        groupe.save()
        messages.success(request, f'Groupe assigné au département {nom_departement}')
    
    # Filtrer les membres disponibles par département
    if nom_departement:
        membres_disponibles = Membre.objects.filter(departement=nom_departement).exclude(groupes_service=groupe)
        # Filtrer aussi les membres actuels du groupe par département
        membres_actuels = groupe.membres.filter(departement=nom_departement)
    else:
        membres_disponibles = Membre.objects.exclude(groupes_service=groupe)
        membres_actuels = groupe.membres.all()
    
    if request.method == 'POST':
        membre_id = request.POST.get('membre_id')
        if membre_id:
            membre = Membre.objects.get(id=membre_id)
            groupe.membres.add(membre)
            messages.success(request, f'{membre.nom_complet} ajouté au groupe!')
        return redirect('gestion_membres_groupe', groupe_id=groupe_id)
    
    context = {
        'groupe': groupe,
        'membres_disponibles': membres_disponibles,
        'membres_actuels': membres_actuels,
        'nom_departement': nom_departement,
    }
    return render(request, 'gestion_membres_groupe.html', context)


@login_required
def gestion_taches_planning(request, planning_id):
    """Définir les tâches pour un planning"""
    planning = PlanningService.objects.get(id=planning_id)
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    # Filtrer les membres par département
    if nom_departement:
        membres = planning.groupe.membres.filter(departement=nom_departement)
    else:
        membres = planning.groupe.membres.all()
    
    if request.method == 'POST':
        tache = request.POST.get('tache')
        membre_id = request.POST.get('membre_id')
        
        if not planning.assignations:
            planning.assignations = {}
        
        if tache not in planning.assignations:
            planning.assignations[tache] = []
        
        if membre_id and membre_id not in planning.assignations[tache]:
            planning.assignations[tache].append(int(membre_id))
        
        planning.save()
        messages.success(request, 'Tâche assignée avec succès!')
        return redirect('gestion_taches_planning', planning_id=planning_id)
    
    context = {
        'planning': planning,
        'membres': membres,
        'nom_departement': nom_departement,
    }
    return render(request, 'gestion_taches_planning.html', context)


@login_required
def suivi_planning(request, planning_id):
    """Suivi de l'exécution d'un planning"""
    planning = PlanningService.objects.get(id=planning_id)
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    if request.method == 'POST':
        planning.notes = request.POST.get('notes', '')
        planning.save()
        messages.success(request, 'Suivi mis à jour!')
        return redirect('suivi_planning', planning_id=planning_id)
    
    context = {
        'planning': planning,
        'nom_departement': nom_departement,
    }
    return render(request, 'suivi_planning.html', context)


@login_required
def supprimer_groupe(request, groupe_id):
    """Supprimer un groupe de service"""
    groupe = get_object_or_404(GroupeService, id=groupe_id)
    
    # Vérifier les permissions
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.RESPONSABLE:
            if groupe.departement != nom_departement:
                messages.error(request, 'Vous ne pouvez supprimer que les groupes de votre département.')
                return redirect('gestion_services')
    except UserProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        nom_groupe = groupe.nom_groupe
        groupe.delete()
        messages.success(request, f'Groupe "{nom_groupe}" supprimé avec succès!')
    
    return redirect('gestion_services')


@login_required
def supprimer_planning(request, planning_id):
    """Supprimer un planning de service"""
    planning = get_object_or_404(PlanningService, id=planning_id)
    
    # Vérifier les permissions
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.RESPONSABLE:
            if planning.groupe.departement != nom_departement:
                messages.error(request, 'Vous ne pouvez supprimer que les plannings de votre département.')
                return redirect('gestion_services')
    except UserProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        type_service = planning.type_service
        date_service = planning.date_service
        planning.delete()
        messages.success(request, f'Planning "{type_service}" du {date_service} supprimé avec succès!')
    
    return redirect('gestion_services')


# ==================== INCIDENT VIEWS ====================

@login_required
def rapport_incident(request):
    """Rapport d'un incident/discipline"""
    
    # Récupérer le département de l'utilisateur
    nom_departement = get_departement_for_user(request.user) if request.user.is_authenticated else None
    
    # Vérifier si l'utilisateur est un responsable ou admin
    is_responsable = False
    is_admin = False
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.role == UserProfile.Role.RESPONSABLE:
                is_responsable = True
            elif profile.role == UserProfile.Role.ADMIN:
                is_admin = True
        except UserProfile.DoesNotExist:
            pass
    
    # Liste des membres : admin voit tout, responsable voit son département
    if is_admin:
        membres = Membre.objects.all().order_by('nom', 'prenom')
    elif is_responsable and nom_departement:
        membres = Membre.objects.filter(departement=nom_departement).order_by('nom', 'prenom')
    else:
        membres = Membre.objects.all().order_by('nom', 'prenom')
    
    context = {
        'membres': membres,
        'nom_departement': nom_departement,
        'is_responsable': is_responsable,
        'is_admin': is_admin,
    }
    
    if request.method == 'POST':
        try:
            incident = Incident(
                type_incident=request.POST.get('type_incident'),
                titre=request.POST.get('titre'),
                description=request.POST.get('description'),
                membre_concerne_id=request.POST.get('membre_concerne'),
                date_incident=request.POST.get('date_incident'),
            )
            
            declare_par_id = request.POST.get('declare_par')
            if declare_par_id:
                incident.declare_par_id = declare_par_id
            
            incident.save()
            messages.success(request, 'Incident signalé avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')

        return redirect('gestion')
    
    return render(request, 'admin/incidents/rapport.html', context)


# ==================== INCIDENTS LIST ====================

@login_required
def liste_incidents(request):
    """Liste des incidents ouverts - Réservé aux administrateurs"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    # Récupérer les incidents ouverts
    incidents = Incident.objects.filter(
        statut__in=[Incident.StatutIncident.OUVERT, Incident.StatutIncident.EN_COURS]
    ).order_by('-date_incident')
    
    # Filtrer par type si spécifié
    type_filter = request.GET.get('type')
    if type_filter:
        incidents = incidents.filter(type_incident=type_filter)
    
    # Statistiques
    en_cours_count = Incident.objects.filter(statut=Incident.StatutIncident.EN_COURS).count()
    resolus_mois = Incident.objects.filter(
        statut=Incident.StatutIncident.RESOLU,
        date_resolution__month=timezone.now().month
    ).count()
    
    paginator = Paginator(incidents, 20)
    page_number = request.GET.get('page')
    incidents_page = paginator.get_page(page_number)
    
    return render(request, 'admin/incidents/liste.html', {
        'incidents': incidents_page,
        'en_cours_count': en_cours_count,
        'resolus_mois_count': resolus_mois
    })


@login_required
def resoudre_incident(request, incident_id):
    """Résoudre un incident"""
    incident = get_object_or_404(Incident, id=incident_id)
    
    if request.method == 'POST':
        incident.statut = Incident.StatutIncident.RESOLU
        incident.resolution = request.POST.get('resolution', '')
        incident.date_resolution = timezone.now().date()
        incident.save()
        messages.success(request, 'Incident marqué comme résolu!')
    
    return redirect('liste_incidents')


# ==================== API VIEWS (JSON) ====================

@csrf_exempt
def api_membres(request):
    """API pour récupérer la liste des membres"""
    membres = Membre.objects.all().values('id', 'nom', 'prenom', 'role', 'status', 'est_sentinelle')
    return JsonResponse(list(membres), safe=False)


@csrf_exempt
def api_statistiques(request):
    """API pour récupérer les statistiques"""
    stats = {
        'total_membres': Membre.objects.count(),
        'membres_actifs': Membre.objects.filter(status=Membre.Status.ACTIF).count(),
        'sentinelles': Membre.objects.filter(est_sentinelle=True).count(),
        'stagiaires': Stagiaire.objects.filter(statut=Stagiaire.StatutStage.EN_COURS).count(),
        'transactions_mois': Transaction.objects.filter(
            date_transaction__month=timezone.now().month
        ).count(),
    }
    return JsonResponse(stats)


@csrf_exempt
def api_presences(request):
    """API pour les présences"""
    if request.method == 'GET':
        date_debut = request.GET.get('date_debut')
        date_fin = request.GET.get('date_fin')
        
        presences = Presence.objects.all()
        
        if date_debut:
            presences = presences.filter(date__gte=date_debut)
        if date_fin:
            presences = presences.filter(date__lte=date_fin)
        
        data = list(presences.values(
            'id', 'membre__nom', 'membre__prenom', 'date', 
            'type_activite', 'status'
        ))
        return JsonResponse(data, safe=False)
    
    elif request.method == 'POST':
        import json
        data = json.loads(request.body)
        
        presence = Presence.objects.create(
            membre_id=data.get('membre'),
            date=data.get('date'),
            type_activite=data.get('type_activite'),
            status=data.get('status'),
            motif_absence=data.get('motif_absence', ''),
        )
        
        return JsonResponse({'success': True, 'id': presence.id})
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@csrf_exempt
def api_responsable_departement(request):
    """API pour récupérer le responsable d'un département"""
    if request.method == 'GET':
        departement_code = request.GET.get('departement')
        
        if not departement_code:
            return JsonResponse({'error': 'Département non spécifié'}, status=400)
        
        # Chercher le responsable du département
        responsable = Membre.objects.filter(
            departement=departement_code,
            est_responsable=True,
            status=Membre.Status.ACTIF
        ).first()
        
        if responsable:
            return JsonResponse({
                'success': True,
                'responsable': {
                    'id': responsable.id,
                    'nom': responsable.nom,
                    'prenom': responsable.prenom,
                    'nom_complet': responsable.nom_complet,
                    'telephone': responsable.telephone,
                    'email': responsable.email,
                }
            })
        else:
            # Chercher un membre du département comme fallback
            membre = Membre.objects.filter(
                departement=departement_code,
                status=Membre.Status.ACTIF
            ).first()
            
            if membre:
                return JsonResponse({
                    'success': True,
                    'responsable': {
                        'id': membre.id,
                        'nom': membre.nom,
                        'prenom': membre.prenom,
                        'nom_complet': f"{membre.prenom} {membre.nom} (Contact)",
                        'telephone': membre.telephone,
                        'email': membre.email,
                    },
                    'note': 'Aucun responsable défini. Premier membre affiché.'
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Aucun membre trouvé pour ce département'
            })
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


# ==================== COMMISSION VIEWS ====================

@login_required
def liste_commissions(request):
    """Liste des commissions avec leurs responsables"""
    commissions = Commission.objects.filter(est_active=True).order_by('nom')
    return render(request, 'commissions/liste.html', {'commissions': commissions})


@login_required
def ajout_commission(request):
    """Ajout ou modification d'une commission"""
    if request.method == 'POST':
        try:
            nom = request.POST.get('nom')
            description = request.POST.get('description', '')
            responsable_id = request.POST.get('responsable')
            
            # Vérifier si la commission existe déjà
            commission = Commission.objects.filter(nom=nom).first()
            
            if commission:
                # Mettre à jour
                commission.description = description
                if responsable_id:
                    commission.responsable_id = responsable_id
                commission.save()
                messages.success(request, 'Commission mise à jour avec succès!')
            else:
                # Créer
                commission = Commission(
                    nom=nom,
                    description=description,
                )
                if responsable_id:
                    commission.responsable_id = responsable_id
                commission.save()
                messages.success(request, 'Commission créée avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('accueil')


@login_required
def assigner_membre_commission(request):
    """Assigner un membre à une commission"""
    if request.method == 'POST':
        try:
            commission_id = request.POST.get('commission_id')
            membre_id = request.POST.get('membre_id')
            
            commission = get_object_or_404(Commission, id=commission_id)
            membre = get_object_or_404(Membre, id=membre_id)
            
            commission.membres.add(membre)
            messages.success(request, f'{membre.prenom} {membre.nom} ajouté à la commission!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('accueil')


# ==================== AUTHENTIFICATION VIEWS ====================

def connexion(request):
    """Vue de connexion utilisateur"""
    if request.user.is_authenticated:
        # Rediriger selon le rôle
        try:
            profile = request.user.profile
            if profile.role == UserProfile.Role.RESPONSABLE:
                return redirect('dashboard_responsable')
            else:
                return redirect('dashboard_admin')
        except UserProfile.DoesNotExist:
            # Créer automatiquement un profil ADMIN si l'utilisateur n'en a pas
            # mais qu'il est un superutilisateur
            if request.user.is_superuser:
                UserProfile.objects.create(
                    user=request.user,
                    role=UserProfile.Role.ADMIN,
                    est_actif=True
                )
                messages.success(request, 'Profil administrateur créé automatiquement.')
                return redirect('dashboard_admin')
            return redirect('dashboard_admin')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Vérifier si le profil existe, sinon le créer
            try:
                profile = user.profile
                if not profile.est_actif:
                    messages.error(request, 'Votre compte a été désactivé. Veuillez contacter l\'administrateur.')
                    return render(request, 'connexion.html')
            except UserProfile.DoesNotExist:
                # Créer automatiquement un profil ADMIN pour les superusers
                if user.is_superuser:
                    UserProfile.objects.create(
                        user=user,
                        role=UserProfile.Role.ADMIN,
                        est_actif=True
                    )
                else:
                    # Pour les utilisateurs normaux sans profil, créer un profil MEMBRE par défaut
                    UserProfile.objects.create(
                        user=user,
                        role=UserProfile.Role.MEMBRE,
                        est_actif=True
                    )
            
            login(request, user)
            
            # Mettre à jour la date de dernière connexion
            try:
                profile = user.profile
                profile.date_derniere_connexion = timezone.now()
                profile.save()
                
                # Rediriger selon le rôle après connexion
                if profile.role == UserProfile.Role.RESPONSABLE:
                    return redirect('dashboard_responsable')
                else:
                    return redirect('dashboard_admin')
            except UserProfile.DoesNotExist:
                # Rediriger vers le dashboard admin par défaut
                return redirect('dashboard_admin')
            
            # Logger l'activité
            ActiviteLog.objects.create(
                utilisateur=user,
                action=ActiviteLog.Action.LOGIN,
                modele='Auth',
                description=f'Connexion de {user.username}',
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'connexion.html')


def get_departement_for_user(user):
    """Helper function to get the department for a user"""
    # Try to find via Departement model first
    try:
        departement = Departement.objects.get(user=user)
        return departement.nom
    except Departement.DoesNotExist:
        pass
    
    # Try via profile -> membre
    try:
        profile = user.profile
        if profile.membre:
            return profile.membre.departement
    except (UserProfile.DoesNotExist, AttributeError):
        pass
    
    return None


def deconnexion(request):
    """Vue de déconnexion utilisateur"""
    if request.user.is_authenticated:
        # Logger l'activité
        ActiviteLog.objects.create(
            utilisateur=request.user,
            action=ActiviteLog.Action.LOGOUT,
            modele='Auth',
            description=f'Déconnexion de {request.user.username}',
            adresse_ip=request.META.get('REMOTE_ADDR')
        )
        logout(request)
        messages.success(request, 'Vous avez été déconnecté avec succès.')
    
    return redirect('connexion')


def inscription(request):
    """Vue d'inscription d'un nouvel utilisateur"""
    if request.user.is_authenticated:
        return redirect('connexion')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validation
        if password != password_confirm:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
            return render(request, 'inscription.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur est déjà utilisé.')
            return render(request, 'inscription.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
            return render(request, 'inscription.html')
        
        # Créer l'utilisateur
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Créer le profil
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.MEMBRE
        )
        
        messages.success(request, 'Compte créé avec succès! Veuillez vous connecter.')
        return redirect('connexion')
    
    return render(request, 'inscription.html')


# ==================== DASHBOARD ADMIN ====================

@login_required
def dashboard_admin(request):
    """Dashboard administrateur avec statistiques avancées"""
    
    # Statistiques des membres
    total_membres = Membre.objects.count()
    membres_actifs = Membre.objects.filter(status=Membre.Status.ACTIF).count()
    membres_inactifs = Membre.objects.filter(status=Membre.Status.INACTIF).count()
    sentinelles = Membre.objects.filter(est_sentinelle=True).count()
    stagaires = Stagiaire.objects.filter(statut=Stagiaire.StatutStage.EN_COURS).count()
    
    # Statistiques financières
    total_entrees = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    total_sorties = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    solde = total_entrees - total_sorties
    
    # Transactions du mois
    transactions_mois = Transaction.objects.filter(
        date_transaction__month=timezone.now().month,
        date_transaction__year=timezone.now().year
    )
    
    # Statistiques des présences (30 derniers jours)
    presences_30_jours = Presence.objects.filter(
        date__gte=timezone.now().date() - timedelta(days=30)
    )
    presences_present = presences_30_jours.filter(status=Presence.StatusPresence.PRESENT).count()
    presences_absent = presences_30_jours.filter(status=Presence.StatusPresence.ABSENT).count()
    
    # Taux de présence
    total_presences = presences_30_jours.count()
    taux_presence = (presences_present / total_presences * 100) if total_presences > 0 else 0
    
    # Événements à venir
    evenements_a_venir = Evenement.objects.filter(
        date_evenement__gte=timezone.now().date()
    ).order_by('date_evenement')[:5]
    
    # Dernières activités
    dernieres_activites = ActiviteLog.objects.all()[:10]
    
    # Dernières notifications non lues
    notifications = Notification.objects.filter(
        utilisateur=request.user,
        est_lu=False
    )[:5]
    
    # Rapports en attente
    rapports_en_attente = RapportCulte.objects.filter(
        statut=RapportCulte.Statut.SOUMIS
    ).count()
    
    # Incidents ouverts
    incidents_ouverts = Incident.objects.filter(
        statut__in=[Incident.StatutIncident.OUVERT, Incident.StatutIncident.EN_COURS]
    ).count()
    
    # Commissions actives
    commissions = Commission.objects.filter(est_active=True)
    
    # Liste des membres pour les formulaires
    membres = Membre.objects.all().order_by('nom', 'prenom')
    
    # Liste des stagiaires (tous les statuts, triés par date)
    stagiaires_liste = Stagiaire.objects.all().select_related('tuteur').order_by('-date_debut')[:20]
    
    # Formations en attente de validation
    formations_en_attente = Formation.objects.filter(
        statut_validation=Formation.StatutValidation.EN_ATTENTE
    ).order_by('-created_at')[:10]
    
    # Données pour les graphiques
    # Présences par jour (7 derniers jours)
    import json
    jours_semaine = []
    presences_par_jour = []
    for i in range(6, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        jours_semaine.append(date.strftime('%d/%m'))
        presences_par_jour.append(
            Presence.objects.filter(date=date, status=Presence.StatusPresence.PRESENT).count()
        )
    
    # Transactions par mois (6 derniers mois)
    mois_six = []
    entrees_par_mois = []
    sorties_par_mois = []
    for i in range(5, -1, -1):
        date = timezone.now().date() - timedelta(days=30*i)
        mois_six.append(date.strftime('%b'))
        entrees = Transaction.objects.filter(
            type_mouvement=Transaction.TypeMouvement.ENTREE,
            date_transaction__month=date.month
        ).aggregate(Sum('montant'))['montant__sum'] or 0
        sorties = Transaction.objects.filter(
            type_mouvement=Transaction.TypeMouvement.SORTIE,
            date_transaction__month=date.month
        ).aggregate(Sum('montant'))['montant__sum'] or 0
        entrees_par_mois.append(float(entrees))
        sorties_par_mois.append(float(sorties))
    
    # Rapports par département (pour le diagramme)
    from django.db.models import Count
    import json
    rapports_par_dept = RapportCulte.objects.values('nom_departement').annotate(total=Count('id')).order_by('-total')
    departements_labels = json.dumps([r['nom_departement'] or 'Non défini' for r in rapports_par_dept])
    departements_counts = json.dumps([r['total'] for r in rapports_par_dept])
    
    context = {
        # Stats membres
        'total_membres': total_membres,
        'membres_actifs': membres_actifs,
        'membres_inactifs': membres_inactifs,
        'sentinelles': sentinelles,
        'stagiaires': stagaires,
        
        # Stats financières
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'solde':solde,
        
        # Stats présences
        'presences_present': presences_present,
        'presences_absent': presences_absent,
        'taux_presence': round(taux_presence, 1),
        
        # Données supplémentaires
        'transactions_mois': transactions_mois.count(),
        'evenements_a_venir': evenements_a_venir,
        'dernieres_activites': dernieres_activites,
        'notifications': notifications,
        'rapports_en_attente': rapports_en_attente,
        'incidents_ouverts': incidents_ouverts,
        'commissions': commissions,
        'membres': membres,
        'stagiaires_liste': stagiaires_liste,
        'formations_en_attente': formations_en_attente,
        
        # Données graphiques
        'jours_semaine': json.dumps(jours_semaine),
        'presences_par_jour': json.dumps(presences_par_jour),
        'mois_six': json.dumps(mois_six),
        'entrees_par_mois': json.dumps(entrees_par_mois),
        'sorties_par_mois': json.dumps(sorties_par_mois),
        'departements_labels': departements_labels,
        'departements_counts': departements_counts,
    }
    
    # Ajouter les transmissions de résumés récentes
    transmissions_recentes = TransmissionResume.objects.select_related('serviteur').order_by('-date_culte')[:10]
    context['transmissions_recentes'] = transmissions_recentes
    
    return render(request, 'admin/dashboard_admin.html', context)


@login_required
def dashboard_responsable(request):
    """Dashboard pour les responsables de département avec les 7 commissions"""
    
    # Vérifier si l'utilisateur est un responsable
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.RESPONSABLE:
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        return redirect('dashboard_admin')
    
    # Récupérer le département du responsable
    nom_departement = get_departement_for_user(request.user)
    
    if not nom_departement:
        messages.error(request, 'Aucun département associé à votre compte.')
        return redirect('connexion')
    
    # Statistiques filtrées par département
    membres = Membre.objects.filter(departement=nom_departement)
    total_membres = membres.count()
    membres_actifs = membres.filter(status=Membre.Status.ACTIF).count()
    
    # Statistiques financières basées sur les transactions du département (créées par l'admin)
    transactions_dept = Transaction.objects.filter(departement=nom_departement)
    total_entrees = transactions_dept.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    total_sorties = transactions_dept.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    solde = total_entrees - total_sorties
    
    # Transactions récentes du département
    transactions_recents = transactions_dept.order_by('-date_transaction')[:5]
    
    # Rapports filtrés par département
    total_rapports = RapportCulte.objects.filter(
        nom_departement=nom_departement
    ).count()
    
    # Stagiaires du département
    stagiaires = Stagiaire.objects.filter(
        statut=Stagiaire.StatutStage.EN_COURS,
        departement_accueil=nom_departement
    )
    nb_stagiaires = stagiaires.count()
    
    # Evénements à venir (tous)
    evenements_a_venir = Evenement.objects.filter(
        date_evenement__gte=timezone.now().date(),
        statut=Evenement.StatutEvenement.PREVU
    ).order_by('date_evenement')[:5]
    
    # Formations (toutes)
    formations = Formation.objects.all().order_by('-date_debut')[:5]
    
    # Groupes de service du département
    from django.db.models import Count
    groupes_dept = list(GroupeService.objects.filter(est_actif=True, departement=nom_departement))
    
    # Plannings de service filtrés par département
    plannings_a_venir = PlanningService.objects.filter(
        groupe__in=groupes_dept,
        date_service__gte=timezone.now().date()
    ).order_by('date_service')[:10]
    
    # Données pour le graphique des groupes
    import json
    groupes_labels = json.dumps([g.nom_groupe for g in groupes_dept[:5]])
    groupes_membres_count = json.dumps([g.membres.count() for g in groupes_dept[:5]])
    
    # Incidents ouverts du département
    incidents_ouverts = Incident.objects.filter(
        membre_concerne__in=membres,
        statut__in=[Incident.StatutIncident.OUVERT, Incident.StatutIncident.EN_COURS]
    ).count()
    
    # Incidents résolus récemment
    incidents_resolus = Incident.objects.filter(
        membre_concerne__in=membres,
        statut__in=[Incident.StatutIncident.RESOLU, Incident.StatutIncident.CLOS]
    ).order_by('-date_resolution')[:10]
    
    # Actualités (toutes)
    actualites = Actualite.objects.filter(est_publie=True).order_by('-date_publication')[:5]
    
    # Notifications
    notifications = Notification.objects.filter(
        utilisateur=request.user,
        est_lu=False
    )[:5]
    
    context = {
        'nom_departement': nom_departement,
        'total_membres': total_membres,
        'membres_actifs': membres_actifs,
        'total_rapports': total_rapports,
        'solde': solde,
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'transactions_recents': transactions_recents,
        'stagiaires': stagiaires,
        'nb_stagiaires': nb_stagiaires,
        'evenements_a_venir': evenements_a_venir,
        'formations': formations,
        'groupes': groupes_dept,
        'plannings_a_venir': plannings_a_venir,
        'incidents_ouverts': incidents_ouverts,
        'incidents_resolus': incidents_resolus,
        'actualites': actualites,
        'notifications': notifications,
        'groupes_labels': groupes_labels,
        'groupes_membres_count': groupes_membres_count,
    }
    
    return render(request, 'responsable/dashboard_responsable.html', context)


# ==================== NOTIFICATIONS ====================

@login_required
def liste_notifications(request):
    """Liste de toutes les notifications de l'utilisateur"""
    notifications = Notification.objects.filter(utilisateur=request.user).order_by('-date_creation')
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    notifications_page = paginator.get_page(page_number)
    
    # Déterminer quel template utiliser en fonction du rôle de l'utilisateur
    is_admin = False
    try:
        if request.user.profile.role == UserProfile.Role.ADMIN:
            is_admin = True
    except (UserProfile.DoesNotExist, AttributeError):
        if request.user.is_superuser:
            is_admin = True

    if is_admin:
        template_name = 'admin/notifications/liste.html'
    else:
        template_name = 'notifications/liste.html'
        
    return render(request, template_name, {'notifications': notifications_page})


@login_required
def marquer_notification_lue(request, notification_id):
    """Marquer une notification comme lue"""
    notification = get_object_or_404(Notification, id=notification_id, utilisateur=request.user)
    notification.est_lu = True
    notification.save()
    
    if notification.lien:
        return redirect(notification.lien)
    return redirect('liste_notifications')


@login_required
def marquer_toutes_notifications_lues(request):
    """Marquer toutes les notifications comme lues"""
    Notification.objects.filter(utilisateur=request.user, est_lu=False).update(est_lu=True)
    messages.success(request, 'Toutes les notifications ont été marquées comme lues.')
    return redirect('liste_notifications')


# ==================== ACTIVITÉS / LOGS ====================

@login_required
def liste_activites(request):
    """Liste des activités du système - Réservé aux administrateurs"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    activites = ActiviteLog.objects.all()
    
    # Filtres
    action_filter = request.GET.get('action')
    if action_filter:
        activites = activites.filter(action=action_filter)
    
    modele_filter = request.GET.get('modele')
    if modele_filter:
        activites = activites.filter(modele=modele_filter)
    
    utilisateur_filter = request.GET.get('utilisateur')
    if utilisateur_filter:
        activites = activites.filter(utilisateur__username__icontains=utilisateur_filter)
    
    paginator = Paginator(activites, 50)
    page_number = request.GET.get('page')
    activites_page = paginator.get_page(page_number)
    
    return render(request, 'activites/liste.html', {'activites': activites_page})


@login_required
def supprimer_activite(request, activite_id):
    """Supprimer une entrée de log d'activité - Réservé aux administrateurs"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    activite = get_object_or_404(ActiviteLog, id=activite_id)
    activite.delete()
    messages.success(request, 'Entrée de log supprimée avec succès!')
    
    # Logger l'activité de suppression
    ActiviteLog.objects.create(
        utilisateur=request.user,
        action=ActiviteLog.Action.DELETE,
        modele='ActiviteLog',
        description=f'Suppression du log ID {activite_id}',
        adresse_ip=request.META.get('REMOTE_ADDR')
    )
    
    return redirect('liste_activites')


@login_required
def supprimer_toutes_activites(request):
    """Supprimer toutes les entrées de log d'activité - Réservé aux administrateurs"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    if request.method == 'POST':
        # Compter avant suppression pour le message
        count = ActiviteLog.objects.count()
        
        # Supprimer tous les logs
        ActiviteLog.objects.all().delete()
        
        messages.success(request, f'{count} entrées de log supprimées avec succès!')
        
        # Logger l'activité de suppression massive
        ActiviteLog.objects.create(
            utilisateur=request.user,
            action=ActiviteLog.Action.DELETE,
            modele='ActiviteLog',
            description=f'Suppression de tous les logs ({count} entrées)',
            adresse_ip=request.META.get('REMOTE_ADDR')
        )
        
        return redirect('liste_activites')
    
    # Si GET, afficher la page de confirmation
    count = ActiviteLog.objects.count()
    return render(request, 'activites/confirmer_suppression.html', {'count': count})


# ==================== GESTION DES MEMBRES AVANCÉE ====================

@login_required
@login_required
def profil_membre(request, membre_id):
    """Profil détaillé d'un membre"""
    membre = get_object_or_404(Membre, id=membre_id)
    
    # Récupérer le nom du département et déterminer le template
    nom_departement = None
    template_name = 'admin/profil_membre.html'
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.RESPONSABLE:
            nom_departement = get_departement_for_user(request.user)
            if membre.departement != nom_departement:
                messages.error(request, 'Vous ne pouvez voir que les membres de votre département.')
                return redirect('liste_membres')
            template_name = 'responsable/profil_membre.html'
    except UserProfile.DoesNotExist:
        pass
    
    # Historique des présences
    presences = Presence.objects.filter(membre=membre).order_by('-date')[:20]
    
    # Transactions
    transactions = Transaction.objects.filter(membre=membre).order_by('-date_transaction')[:10]
    
    # Incidents
    incidents = Incident.objects.filter(membre_concerne=membre).order_by('-date_incident')[:5]
    
    # Fiches de santé spirituelle
    fiches_sante = FicheSanteSpirituelle.objects.filter(membre=membre).order_by('-mois')[:6]
    
    # Commissions
    commissions_membre = membre.commissions.all()
    
    context = {
        'membre': membre,
        'presences': presences,
        'transactions': transactions,
        'incidents': incidents,
        'fiches_sante': fiches_sante,
        'commissions_membre': commissions_membre,
        'nom_departement': nom_departement,
    }
    
    return render(request, template_name, context)


@login_required
def modifier_membre(request, membre_id):
    """Modifier un membre - avec restrictions pour les responsables"""
    membre = get_object_or_404(Membre, id=membre_id)
    
    # Récupérer le nom du département et déterminer le template
    nom_departement = None
    template_name = 'admin/modifier_membre.html'
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.RESPONSABLE:
            nom_departement = get_departement_for_user(request.user)
            if membre.departement != nom_departement:
                messages.error(request, 'Vous ne pouvez modifier que les membres de votre département.')
                return redirect('liste_membres')
            template_name = 'responsable/modifier_membre.html'
    except UserProfile.DoesNotExist:
        messages.error(request, 'Accès non autorisé.')
        return redirect('liste_membres')
    
    if request.method == 'POST':
        membre.nom = request.POST.get('nom')
        membre.prenom = request.POST.get('prenom')
        membre.email = request.POST.get('email')
        membre.telephone = request.POST.get('telephone')
        membre.adresse = request.POST.get('adresse')
        membre.role = request.POST.get('role')
        membre.status = request.POST.get('status')
        membre.est_sentinelle = request.POST.get('est_sentinelle') == 'on'
        membre.groupe_sentinelle = request.POST.get('groupe_sentinelle')
        membre.save()
        
        # Logger l'activité
        ActiviteLog.objects.create(
            utilisateur=request.user,
            action=ActiviteLog.Action.UPDATE,
            modele='Membre',
            objet_id=membre.id,
            description=f'Modification du membre {membre.nom_complet}',
            adresse_ip=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, 'Membre modifié avec succès!')
        return redirect('profil_membre', membre_id=membre.id)
    
    return render(request, template_name, {'membre': membre, 'nom_departement': nom_departement})


@login_required
def supprimer_membre(request, membre_id):
    """Supprimer (désactiver) un membre - avec restrictions pour les responsables"""
    membre = get_object_or_404(Membre, id=membre_id)
    
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.RESPONSABLE:
            # Le responsable ne peut supprimer que les membres de son département
            nom_departement = get_departement_for_user(request.user)
            if membre.departement != nom_departement:
                messages.error(request, 'Vous ne pouvez supprimer que les membres de votre département.')
                return redirect('liste_membres')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Accès non autorisé.')
        return redirect('liste_membres')
    
    if request.method == 'POST':
        membre.status = Membre.Status.INACTIF
        membre.save()
        
        # Logger l'activité
        ActiviteLog.objects.create(
            utilisateur=request.user,
            action=ActiviteLog.Action.DELETE,
            modele='Membre',
            objet_id=membre.id,
            description=f'Désactivation du membre {membre.nom_complet}',
            adresse_ip=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, 'Membre désactivé avec succès!')
        return redirect('liste_membres')
    
    return render(request, 'membres/supprimer.html', {'membre': membre})


# ==================== RAPPORTS AVANCÉS ====================

@login_required
def liste_rapports_culte(request):
    """Liste des rapports de culte - Filtrée par département pour les responsables"""
    # Vérifier le rôle de l'utilisateur
    nom_departement = None
    is_admin = False
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.ADMIN:
            # Admin voit tous les rapports
            rapports = RapportCulte.objects.all().order_by('-date_culte')
            is_admin = True
        elif profile.role == UserProfile.Role.RESPONSABLE:
            # Responsable voit uniquement les rapports de son département
            nom_departement = get_departement_for_user(request.user)
            if nom_departement:
                rapports = RapportCulte.objects.filter(nom_departement=nom_departement).order_by('-date_culte')
            else:
                rapports = RapportCulte.objects.none()
        else:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    # Filtres
    statut_filter = request.GET.get('statut')
    if statut_filter:
        rapports = rapports.filter(statut=statut_filter)
    
    date_debut = request.GET.get('date_debut')
    if date_debut:
        rapports = rapports.filter(date_culte__gte=date_debut)
    
    date_fin = request.GET.get('date_fin')
    if date_fin:
        rapports = rapports.filter(date_culte__lte=date_fin)
    
    paginator = Paginator(rapports, 20)
    page_number = request.GET.get('page')
    rapports_page = paginator.get_page(page_number)
    
    template = 'admin/liste_rapports_culte.html' if is_admin else 'responsable/liste_rapports_culte.html'
    return render(request, template, {'rapports': rapports_page, 'nom_departement': nom_departement})


@login_required
def detail_rapport_culte(request, rapport_id):
    """Détail d'un rapport de culte"""
    rapport = get_object_or_404(RapportCulte, id=rapport_id)
    is_admin = False
    
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.ADMIN:
            is_admin = True
        elif profile.role == UserProfile.Role.RESPONSABLE:
            nom_departement = get_departement_for_user(request.user)
            if rapport.nom_departement != nom_departement:
                messages.error(request, 'Vous n\'avez pas la permission d\'accéder à ce rapport.')
                return redirect('liste_rapports_culte')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('dashboard_admin')
    
    # Récupérer les transmissions de résumés liées à ce rapport
    # Chercher par date exacte OU par date proche (même semaine)
    from datetime import timedelta
    date_debut = rapport.date_culte - timedelta(days=3)
    date_fin = rapport.date_culte + timedelta(days=3)
    
    transmissions = TransmissionResume.objects.filter(
        date_culte__gte=date_debut,
        date_culte__lte=date_fin
    ).order_by('culte')
    
    # Compter les transmissions par culte
    transmission_culte_1 = transmissions.filter(culte__icontains='1er').count()
    transmission_culte_2 = transmissions.filter(culte__icontains='2').count()
    transmission_culte_boss = transmissions.filter(culte__icontains='Boss').count()
    
    template = 'admin/detail_rapport_culte.html' if is_admin else 'responsable/detail_rapport_culte.html'
    return render(request, template, {
        'rapport': rapport,
        'transmissions': transmissions,
        'transmission_culte_1': transmission_culte_1,
        'transmission_culte_2': transmission_culte_2,
        'transmission_culte_boss': transmission_culte_boss,
    })


@login_required
def modifier_rapport_culte(request, rapport_id):
    """Modifier un rapport de culte"""
    rapport = get_object_or_404(RapportCulte, id=rapport_id)
    
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.RESPONSABLE:
            nom_departement = get_departement_for_user(request.user)
            if rapport.nom_departement != nom_departement:
                messages.error(request, 'Vous n\'avez pas la permission de modifier ce rapport.')
                return redirect('liste_rapports_culte')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('dashboard_admin')
    
    if request.method == 'POST':
        try:
            # Mettre à jour tous les champs
            rapport.priere_1_nbre = request.POST.get('priere_1_nbre', 0)
            rapport.priere_1_programme = request.POST.get('priere_1_programme', 0)
            rapport.priere_1_absent = request.POST.get('priere_1_absent', 0)
            rapport.priere_1_motifs = request.POST.get('priere_1_motifs', '')
            
            rapport.culte_1_nbre = request.POST.get('culte_1_nbre', 0)
            rapport.culte_1_programme = request.POST.get('culte_1_programme', 0)
            rapport.culte_1_absent = request.POST.get('culte_1_absent', 0)
            rapport.culte_1_motifs = request.POST.get('culte_1_motifs', '')
            
            rapport.priere_2_nbre = request.POST.get('priere_2_nbre', 0)
            rapport.priere_2_programme = request.POST.get('priere_2_programme', 0)
            rapport.priere_2_absent = request.POST.get('priere_2_absent', 0)
            rapport.priere_2_motifs = request.POST.get('priere_2_motifs', '')
            
            rapport.culte_2_nbre = request.POST.get('culte_2_nbre', 0)
            rapport.culte_2_programme = request.POST.get('culte_2_programme', 0)
            rapport.culte_2_absent = request.POST.get('culte_2_absent', 0)
            rapport.culte_2_motifs = request.POST.get('culte_2_motifs', '')
            
            rapport.culte_boss_nbre = request.POST.get('culte_boss_nbre', 0)
            rapport.culte_boss_programme = request.POST.get('culte_boss_programme', 0)
            rapport.culte_boss_absent = request.POST.get('culte_boss_absent', 0)
            rapport.culte_boss_motifs = request.POST.get('culte_boss_motifs', '')
            
            rapport.reveil_sentinelles_nbre = request.POST.get('reveil_sentinelles_nbre', 0)
            rapport.reveil_sentinelles_programme = request.POST.get('reveil_sentinelles_programme', 0)
            rapport.reveil_sentinelles_absent = request.POST.get('reveil_sentinelles_absent', 0)
            rapport.reveil_sentinelles_motifs = request.POST.get('reveil_sentinelles_motifs', '')
            
            rapport.points_forts = request.POST.get('points_forts', '')
            rapport.difficultes = request.POST.get('difficultes', '')
            rapport.recommandations = request.POST.get('recommandations', '')
            
            rapport.save()
            messages.success(request, 'Rapport modifié avec succès!')
            return redirect('liste_rapports_culte')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return render(request, 'responsable/modifier_rapport.html', {'rapport': rapport})


@login_required
def supprimer_rapport_culte(request, rapport_id):
    """Supprimer un rapport de culte"""
    rapport = get_object_or_404(RapportCulte, id=rapport_id)
    
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role == UserProfile.Role.RESPONSABLE:
            nom_departement = get_departement_for_user(request.user)
            if rapport.nom_departement != nom_departement:
                messages.error(request, 'Vous n\'avez pas la permission de supprimer ce rapport.')
                return redirect('liste_rapports_culte')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('dashboard_admin')
    
    if request.method == 'POST':
        rapport.delete()
        messages.success(request, 'Rapport supprimé avec succès!')
    
    return redirect('liste_rapports_culte')


# ==================== TRANSMISSION RÉSUMÉ CULTE VIEWS ====================

@login_required
def transmission_resume_culte(request):
    """Enregistrement de la transmission des résumés de culte"""
    if request.method == 'POST':
        try:
            # Récupérer le nombre d'entrées
            count = int(request.POST.get('entry_count', 0))

            for i in range(1, count + 1):
                serviteur_id = request.POST.get(f'serviteur_{i}')
                culte = request.POST.get(f'culte_{i}')
                date_culte = request.POST.get(f'date_culte_{i}')
                resume_transmis = request.POST.get(f'resum_transmis_{i}')
                date_transmission = request.POST.get(f'date_transmission_{i}')
                respect_delai = request.POST.get(f'respect_delai_{i}')
                observation = request.POST.get(f'observation_{i}')

                if serviteur_id and culte and date_culte:
                    # Déterminer le statut
                    if resume_transmis == 'Oui':
                        statut = TransmissionResume.StatutTransmission.TRANSMIS
                    elif resume_transmis == 'En retard':
                        statut = TransmissionResume.StatutTransmission.EN_RETARD
                    else:
                        statut = TransmissionResume.StatutTransmission.NON_TRANSMIS

                    # Créer l'entrée
                    TransmissionResume.objects.create(
                        serviteur_id=serviteur_id,
                        culte=culte,
                        date_culte=date_culte,
                        date_transmission=date_transmission if date_transmission else None,
                        statut=statut,
                        respect_delai=respect_delai == 'Oui',
                        observation=observation or ''
                    )

            # Vérifier si c'est une requête AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Transmission des résumés enregistrée avec succès!'})
            
            messages.success(request, 'Transmission des résumés enregistrée avec succès!')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, f'Erreur: {str(e)}')

    return redirect('gestion')


# ==================== GESTION DES RESPONSABLES DE DÉPARTEMENTS ====================

@login_required
def liste_responsables(request):
    """Liste des responsables de départements"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role not in [UserProfile.Role.ADMIN, UserProfile.Role.RESPONSABLE]:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    departements = Departement.objects.filter(est_actif=True).order_by('nom')
    
    context = {
        'departements': departements,
    }
    
    return render(request, 'admin/responsables/liste.html', context)


@login_required
def creer_responsable(request):
    """Créer un responsable de département avec compte utilisateur"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    if request.method == 'POST':
        try:
            departement_code = request.POST.get('departement')
            membre_id = request.POST.get('membre')
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            # Validation
            if not departement_code or not membre_id or not username or not password:
                messages.error(request, 'Tous les champs sont obligatoires.')
                return redirect('creer_responsable')
            
            # Vérifier si le département existe
            departement = Departement.objects.filter(nom=departement_code).first()
            if not departement:
                departement = Departement.objects.create(nom=departement_code)
            
            # Vérifier si le membre existe
            membre = get_object_or_404(Membre, id=membre_id)
            
            # Vérifier si l'utilisateur existe déjà
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
                return redirect('creer_responsable')
            
            # Créer l'utilisateur
            user = User.objects.create_user(
                username=username,
                password=password,
                email=membre.email if membre.email else '',
                first_name=membre.prenom,
                last_name=membre.nom
            )
            
            # Créer le profil avec le rôle RESPONSABLE
            UserProfile.objects.create(
                user=user,
                membre=membre,
                role=UserProfile.Role.RESPONSABLE,
                peut_creer_rapport=True,
                peut_gerer_membres=False,
                peut_gerer_finances=False,
                peut_gerer_formations=True,
                peut_publier_actualites=True,
                peut_gerer_commissions=False
            )
            
            # Mettre à jour le département
            departement.responsable = membre
            departement.user = user
            departement.save()
            
            # Mettre à jour le membre
            membre.departement = departement_code
            membre.est_responsable = True
            membre.save()
            
            # Créer une notification pour le responsable
            Notification.objects.create(
                utilisateur=user,
                type=Notification.Type.SUCCESS,
                titre='Compte créé',
                message=f'Votre compte de responsable du département {departement.get_nom_display()} a été créé. '
                        f'Vos identifiants: Username: {username}',
                lien=''
            )
            
            # Logger l'activité
            ActiviteLog.objects.create(
                utilisateur=request.user,
                action=ActiviteLog.Action.CREATE,
                modele='Departement',
                objet_id=departement.id,
                description=f'Création du responsable {username} pour le département {departement.get_nom_display()}',
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Responsable créé avec succès! Identifiants: Username: {username}, Mot de passe: {password}')
            return redirect('liste_responsables')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
            return redirect('creer_responsable')
    
    # GET request
    departements = Departement.NomDepartement.choices
    membres = Membre.objects.filter(status=Membre.Status.ACTIF).order_by('nom', 'prenom')
    
    # Departements qui n'ont pas encore de responsable
    departements_occupes = Departement.objects.exclude(user__isnull=True).values_list('nom', flat=True)
    departements_disponibles = [d for d in departements if d[0] not in departements_occupes]
    
    context = {
        'departements': departements_disponibles,
        'membres': membres,
    }
    
    return render(request, 'admin/responsables/creer.html', context)


@login_required
def modifier_responsable(request, departement_id):
    """Modifier un responsable de département"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    departement = get_object_or_404(Departement, id=departement_id)
    
    if request.method == 'POST':
        try:
            membre_id = request.POST.get('membre')
            new_password = request.POST.get('new_password')
            
            # Mettre à jour le membre
            if membre_id:
                ancien_responsable = departement.responsable
                nouveau_responsable = get_object_or_404(Membre, id=membre_id)
                
                # Retirer l'ancien responsable
                if ancien_responsable:
                    ancien_responsable.est_responsable = False
                    ancien_responsable.save()
                
                # Assigner le nouveau responsable
                departement.responsable = nouveau_responsable
                nouveau_responsable.est_responsable = True
                nouveau_responsable.departement = departement.nom
                nouveau_responsable.save()
            
            # Changer le mot de passe si fourni
            if new_password and departement.user:
                departement.user.set_password(new_password)
                departement.user.save()
                
                # Notifier le responsable
                Notification.objects.create(
                    utilisateur=departement.user,
                    type=Notification.Type.INFO,
                    titre='Mot de passe modifié',
                    message='Votre mot de passe a été modifié par l\'administrateur.',
                    lien=''
                )
            
            departement.save()
            
            # Logger l'activité
            ActiviteLog.objects.create(
                utilisateur=request.user,
                action=ActiviteLog.Action.UPDATE,
                modele='Departement',
                objet_id=departement.id,
                description=f'Modification du responsable du département {departement.get_nom_display()}',
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Responsable modifié avec succès!')
            return redirect('liste_responsables')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    membres = Membre.objects.filter(status=Membre.Status.ACTIF).order_by('nom', 'prenom')
    
    context = {
        'departement': departement,
        'membres': membres,
    }
    
    return render(request, 'admin/responsables/modifier.html', context)


@login_required
def supprimer_responsable(request, departement_id):
    """Supprimer (désactiver) un responsable de département"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    departement = get_object_or_404(Departement, id=departement_id)
    
    if request.method == 'POST':
        try:
            # Désactiver le membre
            if departement.responsable:
                departement.responsable.est_responsable = False
                departement.responsable.save()
            
            # Désactiver le compte utilisateur
            if departement.user:
                departement.user.is_active = False
                departement.user.save()
                
                # Notifier l'utilisateur
                Notification.objects.create(
                    utilisateur=departement.user,
                    type=Notification.Type.WARNING,
                    titre='Compte désactivé',
                    message='Votre compte de responsable a été désactivé.',
                    lien=''
                )
            
            # Logger l'activité
            ActiviteLog.objects.create(
                utilisateur=request.user,
                action=ActiviteLog.Action.DELETE,
                modele='Departement',
                objet_id=departement.id,
                description=f'Suppression du responsable du département {departement.get_nom_display()}',
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Responsable supprimé avec succès!')
            return redirect('liste_responsables')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('liste_responsables')


@login_required
def reinitialiser_mot_de_passe(request, departement_id):
    """Réinitialiser le mot de passe d'un responsable"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    departement = get_object_or_404(Departement, id=departement_id)
    
    if request.method == 'POST':
        try:
            new_password = request.POST.get('new_password')
            
            if not new_password:
                messages.error(request, 'Le nouveau mot de passe est obligatoire.')
                return redirect('liste_responsables')
            
            if departement.user:
                departement.user.set_password(new_password)
                departement.user.save()
                
                # Notifier le responsable
                Notification.objects.create(
                    utilisateur=departement.user,
                    type=Notification.Type.INFO,
                    titre='Mot de passe réinitialisé',
                    message=f'Votre mot de passe a été réinitialisé. Nouveau mot de passe: {new_password}',
                    lien=''
                )
                
                messages.success(request, f'Mot de passe réinitialisé! Nouveau mot de passe: {new_password}')
            else:
                messages.error(request, 'Ce département n\'a pas de compte utilisateur.')
                
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('liste_responsables')


# ==================== COMMISSION TRESOR FINANCE VIEWS ====================

@login_required
def tresor_finance(request):
    """Vue principale de la commission Trésor, Finance et Gestion des Ressources"""
    
    # Vérifier les permissions (Admin, Trésorier ou Responsable)
    try:
        profile = request.user.profile
        if profile.role not in [UserProfile.Role.ADMIN, UserProfile.Role.TRESORIER, UserProfile.Role.RESPONSABLE]:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    # Statistiques financières
    total_entrees = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    total_sorties = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    solde = total_entrees - total_sorties
    
    # Transactions récentes
    transactions_recents = Transaction.objects.order_by('-date_transaction')[:10]
    
    # Impayés - Statistiques
    impayes_en_retard = Impayes.objects.filter(
        statut__in=[Impayes.StatutImpaye.EN_RETARD, Impayes.StatutImpaye.RELANCE]
    )
    total_impayes = impayes_en_retard.aggregate(Sum('montant_restant'))['montant_restant__sum'] or 0
    nb_impayes = impayes_en_retard.count()
    
    # Budgets
    budgets = Budget.objects.order_by('-annee', '-mois')[:6]
    budgets_annee_courante = Budget.objects.filter(annee=timezone.now().year)
    
    # Transactions du mois en cours
    transactions_mois = Transaction.objects.filter(
        date_transaction__month=timezone.now().month,
        date_transaction__year=timezone.now().year
    )
    entrees_mois = transactions_mois.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    sorties_mois = transactions_mois.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    # Membres pour les formulaires
    membres = Membre.objects.filter(status=Membre.Status.ACTIF).order_by('nom', 'prenom')
    
    # Commissions
    commission_tresor = Commission.objects.filter(nom=Commission.NomCommission.TRESOR_FINANCE).first()
    
    context = {
        # Statistiques financières
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'solde': solde,
        'transactions_recents': transactions_recents,
        
        # Impayés
        'impayes_en_retard': impayes_en_retard[:10],
        'total_impayes': total_impayes,
        'nb_impayes': nb_impayes,
        
        # Budgets
        'budgets': budgets,
        'budgets_annee_courante': budgets_annee_courante,
        
        # Transactions du mois
        'entrees_mois': entrees_mois,
        'sorties_mois': sorties_mois,
        
        # Autres données
        'membres': membres,
        'commission_tresor': commission_tresor,
    }
    
    return render(request, 'tresor_finance.html', context)


@login_required
def ajout_impaye(request):
    """Ajouter un nouvel impayé"""
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role not in [UserProfile.Role.ADMIN, UserProfile.Role.TRESORIER]:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    if request.method == 'POST':
        try:
            impaye = Impayes(
                membre_id=request.POST.get('membre'),
                type_cotisation=request.POST.get('type_cotisation', 'COTISATION'),
                montant_du=request.POST.get('montant_du'),
                montant_paye=request.POST.get('montant_paye', 0),
                periode_debut=request.POST.get('periode_debut'),
                periode_fin=request.POST.get('periode_fin') or None,
                date_echeance=request.POST.get('date_echeance'),
                observations=request.POST.get('observations', ''),
            )
            impaye.save()
            messages.success(request, 'Impayé enregistré avec succès!')
            
            # Logger l'activité
            ActiviteLog.objects.create(
                utilisateur=request.user,
                action=ActiviteLog.Action.CREATE,
                modele='Impayes',
                objet_id=impaye.id,
                description=f'Enregistrement d\'un impayé pour {impaye.membre.nom_complet}',
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('tresor_finance')


@login_required
def payer_impaye(request, impaye_id):
    """Enregistrer un paiement pour un impayé"""
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role not in [UserProfile.Role.ADMIN, UserProfile.Role.TRESORIER]:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    impaye = get_object_or_404(Impayes, id=impaye_id)
    
    if request.method == 'POST':
        try:
            montant_paye = Decimal(request.POST.get('montant_paye', 0))
            impaye.montant_paye += montant_paye
            
            if impaye.montant_paye >= impaye.montant_du:
                impaye.statut = Impayes.StatutImpaye.SOLDE
                impaye.date_paiement = timezone.now().date()
            elif impaye.montant_paye > 0:
                impaye.statut = Impayes.StatutImpaye.PAIE_PARTIEL
            
            impaye.save()
            
            # Logger l'activité
            ActiviteLog.objects.create(
                utilisateur=request.user,
                action=ActiviteLog.Action.UPDATE,
                modele='Impayes',
                objet_id=impaye.id,
                description=f'Paiement de {montant_paye} CFA pour l\'impayé de {impaye.membre.nom_complet}',
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Paiement enregistré avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('tresor_finance')


@login_required
def relancer_impaye(request, impaye_id):
    """Envoyer une relance pour un impayé"""
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role not in [UserProfile.Role.ADMIN, UserProfile.Role.TRESORIER]:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    impaye = get_object_or_404(Impayes, id=impaye_id)
    
    # Incrémenter le nombre de relances
    impaye.nb_relances += 1
    impaye.date_derniere_relance = timezone.now().date()
    impaye.statut = Impayes.StatutImpaye.RELANCE
    impaye.save()
    
    # Créer une notification pour le membre
    if impaye.membre.user:
        Notification.objects.create(
            utilisateur=impaye.membre.user,
            type=Notification.Type.WARNING,
            title='Relance paiement',
            message=f'Bonjour {impaye.membre.prenom}, nous vous rappelons que votre cotisation de {impaye.montant_restant} CFA est en attente. Merci de regulariser votre situation.',
            lien=''
        )
    
    messages.success(request, f'Relance envoyée à {impaye.membre.nom_complet}!')
    
    return redirect('tresor_finance')


@login_required
def creer_budget(request):
    """Créer un nouveau budget"""
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role not in [UserProfile.Role.ADMIN, UserProfile.Role.TRESORIER]:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    if request.method == 'POST':
        try:
            annee = int(request.POST.get('annee'))
            mois = request.POST.get('mois')
            mois = int(mois) if mois else None
            
            # Vérifier si le budget existe déjà
            existing_budget = Budget.objects.filter(
                annee=annee,
                mois=mois,
                categorie=request.POST.get('categorie')
            ).first()
            
            if existing_budget:
                # Mettre à jour
                existing_budget.montant_prevu = request.POST.get('montant_prevu')
                existing_budget.notes = request.POST.get('notes', '')
                existing_budget.save()
                messages.success(request, 'Budget mis à jour avec succès!')
            else:
                # Créer
                budget = Budget(
                    annee=annee,
                    mois=mois,
                    categorie=request.POST.get('categorie'),
                    montant_prevu=request.POST.get('montant_prevu'),
                    notes=request.POST.get('notes', ''),
                )
                budget.save()
                messages.success(request, 'Budget créé avec succès!')
            
            # Logger l'activité
            ActiviteLog.objects.create(
                utilisateur=request.user,
                action=ActiviteLog.Action.CREATE,
                modele='Budget',
                description=f'Creation du budget {request.POST.get("categorie")} pour {annee}',
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('tresor_finance')


@login_required
def suivre_budget(request):
    """Suivre l'exécution des budgets"""
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role not in [UserProfile.Role.ADMIN, UserProfile.Role.TRESORIER, UserProfile.Role.RESPONSABLE]:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    annee = request.GET.get('annee', timezone.now().year)
    try:
        annee = int(annee)
    except ValueError:
        annee = timezone.now().year
    
    # Récupérer les budgets de l'année
    budgets = Budget.objects.filter(annee=annee).order_by('mois', 'categorie')
    
    # Calculer les montants réels pour chaque budget
    for budget in budgets:
        transactions = Transaction.objects.filter(
            categorie=budget.categorie,
            date_transaction__year=annee
        )
        if budget.mois:
            transactions = transactions.filter(date_transaction__month=budget.mois)
        
        budget.montant_realise = transactions.filter(
            type_mouvement=Transaction.TypeMouvement.SORTIE
        ).aggregate(Sum('montant'))['montant__sum'] or 0
        budget.save()
    
    # Statistiques globales
    total_prevu = budgets.aggregate(Sum('montant_prevu'))['montant_prevu__sum'] or 0
    total_realise = budgets.aggregate(Sum('montant_realise'))['montant_realise__sum'] or 0
    
    context = {
        'budgets': budgets,
        'annee': annee,
        'total_prevu': total_prevu,
        'total_realise': total_realise,
        'taux_execution': (total_realise / total_prevu * 100) if total_prevu > 0 else 0,
    }
    
    return render(request, 'suivre_budget.html', context)


@login_required
def liste_impayes(request):
    """Liste complète des impayés"""
    # Vérifier les permissions
    try:
        profile = request.user.profile
        if profile.role not in [UserProfile.Role.ADMIN, UserProfile.Role.TRESORIER]:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    # Filtres
    statut = request.GET.get('statut')
    impayes = Impayes.objects.all().order_by('-date_echeance')
    
    if statut:
        impayes = impayes.filter(statut=statut)
    
    # Filtrer les impayés en retard
    impayes_en_retard = impayes.filter(
        statut__in=[Impayes.StatutImpaye.EN_RETARD, Impayes.StatutImpaye.RELANCE]
    )
    
    paginator = Paginator(impayes, 20)
    page_number = request.GET.get('page')
    impayes_page = paginator.get_page(page_number)
    
    context = {
        'impayes': impayes_page,
        'impayes_en_retard': impayes_en_retard,
        'statut_filter': statut,
    }
    
    return render(request, 'liste_impayes.html', context)


@login_required
def liste_stagiaires(request):
    """Liste de tous les stagiaires - Réservé aux administrateurs"""
    # Vérifier les permissions admin
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil. Veuillez contacter l\'administrateur.')
        return redirect('dashboard_admin')
    
    # Filtres
    statut_filtre = request.GET.get('statut', '')
    departement_filtre = request.GET.get('departement', '')
    
    # Requête de base
    stagiaires = Stagiaire.objects.all().select_related('tuteur').order_by('-date_debut')
    
    # Appliquer les filtres
    if statut_filtre:
        stagiaires = stagiaires.filter(statut=statut_filtre)
    if departement_filtre:
        stagiaires = stagiaires.filter(departement_accueil__icontains=departement_filtre)
    
    # Statistiques
    total_stagiaires = Stagiaire.objects.count()
    stagiaires_en_cours = Stagiaire.objects.filter(statut=Stagiaire.StatutStage.EN_COURS).count()
    stagiaires_termines = Stagiaire.objects.filter(statut=Stagiaire.StatutStage.TERMINE).count()
    
    # Récupérer les départements uniques
    departements = Stagiaire.objects.values_list('departement_accueil', flat=True).distinct()
    
    context = {
        'stagiaires': stagiaires,
        'total_stagiaires': total_stagiaires,
        'stagiaires_en_cours': stagiaires_en_cours,
        'stagiaires_termines': stagiaires_termines,
        'departements': departements,
        'statut_filtre': statut_filtre,
        'departement_filtre': departement_filtre,
    }
    
    return render(request, 'admin/liste_stagiaires.html', context)


@login_required
def supprimer_stagiaire(request, stagiaire_id):
    """Supprimer un stagiaire - Réservé aux administrateurs"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('liste_stagiaires')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('liste_stagiaires')
    
    stagiaire = get_object_or_404(Stagiaire, id=stagiaire_id)
    
    if request.method == 'POST':
        nom_complet = f"{stagiaire.prenom} {stagiaire.nom}"
        stagiaire.delete()
        messages.success(request, f'Stagiaire {nom_complet} supprimé avec succès!')
    
    return redirect('liste_stagiaires')


@login_required
def valider_formation(request, formation_id):
    """Valider une formation - Réservé aux administrateurs"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('liste_formations')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('liste_formations')
    
    formation = get_object_or_404(Formation, id=formation_id)
    formation.statut_validation = Formation.StatutValidation.VALIDEE
    formation.save()
    
    messages.success(request, f'Formation "{formation.titre}" validée avec succès!')
    return redirect('liste_formations')


@login_required
def rejeter_formation(request, formation_id):
    """Rejeter une formation - Réservé aux administrateurs"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'effectuer cette action.')
            return redirect('liste_formations')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('liste_formations')
    
    formation = get_object_or_404(Formation, id=formation_id)
    formation.statut_validation = Formation.StatutValidation.REJETEE
    formation.save()
    
    messages.warning(request, f'Formation "{formation.titre}" rejetée.')
    return redirect('liste_formations')


@login_required
def modifier_formation(request, formation_id):
    """Modifier une formation"""
    formation = get_object_or_404(Formation, id=formation_id)
    
    if request.method == 'POST':
        try:
            formation.titre = request.POST.get('titre')
            formation.description = request.POST.get('description')
            formation.date_debut = request.POST.get('date_debut')
            formation.date_fin = request.POST.get('date_fin')
            formation.lieu = request.POST.get('lieu', '')
            formation.est_en_ligne = request.POST.get('est_en_ligne') == 'on'
            formation.lien_online = request.POST.get('lien_online', '')
            formation.departement = request.POST.get('departement_destinataire', '')
            
            if request.FILES.get('supports'):
                formation.supports = request.FILES.get('supports')
            if request.FILES.get('video'):
                formation.video = request.FILES.get('video')
            if request.FILES.get('image'):
                formation.image = request.FILES.get('image')
            
            formation.save()
            messages.success(request, 'Formation modifiée avec succès!')
            return redirect('liste_formations')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('liste_formations')


@login_required
def supprimer_formation(request, formation_id):
    """Supprimer une formation"""
    formation = get_object_or_404(Formation, id=formation_id)
    formation.delete()
    messages.success(request, 'Formation supprimée avec succès!')
    return redirect('liste_formations')


# ==================== GESTION DU PROFIL ADMIN ====================

@login_required
def modifier_profil_admin(request):
    """Vue pour modifier le profil de l'admin (username et mot de passe)"""
    user = request.user
    
    # Vérifier que c'est un admin (soit par profil, soit par superuser)
    is_admin = False
    try:
        if hasattr(user, 'profile'):
            if user.profile.role == UserProfile.Role.ADMIN:
                is_admin = True
    except:
        pass
    
    # Allow superusers as well
    if user.is_superuser:
        is_admin = True
    
    if not is_admin:
        messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
        return redirect('dashboard_admin')
    
    user = request.user
    
    if request.method == 'POST':
        new_username = request.POST.get('new_username', '').strip()
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        new_password_confirm = request.POST.get('new_password_confirm', '')
        
        # Vérifier le mot de passe actuel
        if not user.check_password(current_password):
            messages.error(request, 'Le mot de passe actuel est incorrect.')
            return render(request, 'admin/modifier_profil.html', {'user': user})
        
        # Changer le username si fourni et différent
        if new_username and new_username != user.username:
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                messages.error(request, 'Ce nom d\'utilisateur est déjà utilisé.')
                return render(request, 'admin/modifier_profil.html', {'user': user})
            user.username = new_username
            messages.success(request, 'Nom d\'utilisateur modifié avec succès!')
        
        # Changer le mot de passe si fourni
        if new_password:
            if len(new_password) < 8:
                messages.error(request, 'Le mot de passe doit contenir au moins 8 caractères.')
                return render(request, 'admin/modifier_profil.html', {'user': user})
            
            if new_password != new_password_confirm:
                messages.error(request, 'Les nouveaux mots de passe ne correspondent pas.')
                return render(request, 'admin/modifier_profil.html', {'user': user})
            
            user.set_password(new_password)
            user.save()
            
            # Re-authentifier l'utilisateur avec le nouveau mot de passe
            login(request, user)
            messages.success(request, 'Mot de passe modifié avec succès!')
        
        # Sauvegarder les changements de username
        if new_username and new_username != request.user.username:
            user.save()
        
        return redirect('dashboard_admin')
    
    return render(request, 'admin/modifier_profil.html', {'user': user})


# ==================== ÉVÉNEMENTS VIEWS ====================

@login_required
def liste_evenements(request):
    """Liste de tous les événements - Réservé aux administrateurs"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('dashboard_admin')
    
    evenements = Evenement.objects.all().order_by('-date_evenement')
    
    # Préparer les données JSON pour le modal
    import json
    evenements_json = json.dumps([{
        'id': e.id,
        'titre': e.titre,
        'type_evenement': e.get_type_evenement_display(),
        'date_evenement': e.date_evenement.strftime('%d/%m/%Y'),
        'heure': e.heure.strftime('%H:%M') if e.heure else '',
        'lieu': e.lieu,
        'description': e.description,
        'montant_collecte': str(e.montant_collecte),
        'montant_depense': str(e.montant_depense),
        'statut': e.statut,
        'statut_display': e.get_statut_display(),
    } for e in evenements])
    
    context = {
        'evenements': evenements,
        'evenements_json': evenements_json,
    }
    
    return render(request, 'admin/liste_evenements.html', context)


@login_required
def marquer_evenement_realise(request, evenement_id):
    """Marquer un événement comme réalisé"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission.')
            return redirect('liste_evenements')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('liste_evenements')
    
    evenement = get_object_or_404(Evenement, id=evenement_id)
    
    if request.method == 'POST':
        evenement.statut = Evenement.StatutEvenement.REALISE
        evenement.save()
        messages.success(request, f'Événement "{evenement.titre}" marqué comme réalisé!')
    
    return redirect('liste_evenements')


@login_required
def marquer_evenement_prevu(request, evenement_id):
    """Marquer un événement comme prévu (non réalisé)"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission.')
            return redirect('liste_evenements')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('liste_evenements')
    
    evenement = get_object_or_404(Evenement, id=evenement_id)
    
    if request.method == 'POST':
        evenement.statut = Evenement.StatutEvenement.PREVU
        evenement.save()
        messages.success(request, f'Événement "{evenement.titre}" marqué comme non réalisé!')
    
    return redirect('liste_evenements')


@login_required
def export_evenements_pdf(request):
    """Exporter les événements du mois en PDF"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission.')
            return redirect('liste_evenements')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('liste_evenements')
    
    from django.http import HttpResponse
    from datetime import datetime
    
    # Récupérer les événements du mois en cours
    now = timezone.now()
    evenements = Evenement.objects.filter(
        date_evenement__month=now.month,
        date_evenement__year=now.year
    ).order_by('date_evenement')
    
    # Créer le contenu HTML pour impression
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Événements - {now.strftime('%B %Y')}</title>
    <style>
        @media print {{
            body {{ margin: 0; }}
        }}
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #FFD700; text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #FFD700; color: black; }}
        .realise {{ color: green; font-weight: bold; }}
        .prevu {{ color: orange; font-weight: bold; }}
        .annule {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Événements - {now.strftime('%B %Y')}</h1>
    <p>Date d'export: {now.strftime('%d/%m/%Y %H:%M')}</p>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Titre</th>
                <th>Type</th>
                <th>Lieu</th>
                <th>Statut</th>
            </tr>
        </thead>
        <tbody>"""
    
    for evt in evenements:
        statut_class = 'realise' if evt.statut == 'REALISE' else 'annule' if evt.statut == 'ANNULE' else 'prevu'
        html_content += f"""
            <tr>
                <td>{evt.date_evenement.strftime('%d/%m/%Y')}</td>
                <td>{evt.titre}</td>
                <td>{evt.get_type_evenement_display()}</td>
                <td>{evt.lieu or '-'}</td>
                <td class="{statut_class}">{evt.get_statut_display()}</td>
            </tr>"""
    
    html_content += """
        </tbody>
    </table>
    <script>window.print();</script>
</body>
</html>"""
    
    response = HttpResponse(html_content, content_type='text/html')
    return response


@login_required
def supprimer_evenement(request, evenement_id):
    """Supprimer un événement"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission.')
            return redirect('liste_evenements')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('liste_evenements')
    
    evenement = get_object_or_404(Evenement, id=evenement_id)
    
    if request.method == 'POST':
        titre = evenement.titre
        evenement.delete()
        messages.success(request, f'Événement "{titre}" supprimé avec succès!')
    
    return redirect('liste_evenements')


@login_required
def modifier_statut_stagiaire(request, stagiaire_id):
    """Modifier le statut d'un stagiaire"""
    stagiaire = get_object_or_404(Stagiaire, id=stagiaire_id)
    
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in dict(Stagiaire.StatutStage.choices):
            stagiaire.statut = nouveau_statut
            if nouveau_statut == Stagiaire.StatutStage.TERMINE:
                stagiaire.date_fin = timezone.now().date()
            stagiaire.save()
            messages.success(request, f'Statut du stagiaire {stagiaire.prenom} {stagiaire.nom} modifié avec succès!')
        else:
            messages.error(request, 'Statut invalide.')
    
    return redirect('communion')


@login_required
def export_finances_pdf(request):
    """Exporter les finances en PDF"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('dashboard_admin')
    
    from .utils import generer_pdf_finances
    
    # Statistiques financières
    total_entrees = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.ENTREE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    total_sorties = Transaction.objects.filter(
        type_mouvement=Transaction.TypeMouvement.SORTIE
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    solde = total_entrees - total_sorties
    
    # Toutes les transactions
    transactions = Transaction.objects.all().order_by('-date_transaction')
    
    return generer_pdf_finances(transactions, total_entrees, total_sorties, solde)


@login_required
def export_recapitulatif_pdf(request):
    """Exporter un PDF récapitulatif de toutes les activités des départements"""
    try:
        profile = request.user.profile
        if profile.role != UserProfile.Role.ADMIN:
            messages.error(request, 'Vous n\'avez pas la permission.')
            return redirect('dashboard_admin')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Vous n\'avez pas de profil.')
        return redirect('dashboard_admin')
    
    # Récupérer les données du mois en cours
    now = timezone.now()
    
    # Rapports de culte
    rapports = RapportCulte.objects.filter(
        date_culte__month=now.month,
        date_culte__year=now.year
    ).select_related('responsable').order_by('nom_departement', '-date_culte')
    
    # Transactions
    transactions = Transaction.objects.filter(
        date_transaction__month=now.month,
        date_transaction__year=now.year
    ).exclude(departement='').order_by('departement', '-date_transaction')
    
    # Événements
    evenements = Evenement.objects.filter(
        date_evenement__month=now.month,
        date_evenement__year=now.year
    ).select_related('responsable').order_by('date_evenement')
    
    # Stagiaires
    stagiaires = Stagiaire.objects.filter(
        statut=Stagiaire.StatutStage.EN_COURS
    ).select_related('tuteur').order_by('departement_accueil', 'nom')
    
    return generer_pdf_recapitulatif(rapports, transactions, evenements, stagiaires)
