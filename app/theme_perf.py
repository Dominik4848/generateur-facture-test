"""Accélère le dessin du thème Azure, sans changer son apparence.

Les éléments du thème sont des images de 20×20 ou 50×50 px découpées en 9 (coins, bords, centre) :
pour couvrir un champ ou un cadre, ttk répète le centre et les bords en centaines de petits morceaux,
chacun avec un mélange de transparence. C'est ce qui rend le défilement lent.

Avant de charger le thème, on intercepte `ttk::style element create ... image` : chaque image
« étirable » (bords et centre uniformes) est remplacée par une copie agrandie, où la colonne et la
ligne du milieu sont répétées. Le rendu est identique au pixel près, mais ttk dessine le centre
en un ou quelques morceaux. -width / -height gardent la taille minimale d'origine des widgets.
"""

STRETCH_PX = 300

TCL_HOOK = r"""
namespace eval ::theme_perf {
    variable cache
    array set cache {}
    variable extra @EXTRA@

    # Vrai si toutes les colonnes de [b, w-b[ sont identiques, et de même pour les lignes :
    # répéter celle du milieu ne change alors rien au rendu.
    proc uniform {img b} {
        set w [image width $img]
        set h [image height $img]
        if {$w <= 2 * $b + 1 || $h <= 2 * $b + 1} { return 0 }
        set mx [expr {$w / 2}]
        set my [expr {$h / 2}]
        for {set y 0} {$y < $h} {incr y} {
            set ref [$img get $mx $y]
            set tref [$img transparency get $mx $y]
            for {set x $b} {$x < $w - $b} {incr x} {
                if {[$img get $x $y] ne $ref || [$img transparency get $x $y] != $tref} { return 0 }
            }
        }
        for {set x 0} {$x < $w} {incr x} {
            set ref [$img get $x $my]
            set tref [$img transparency get $x $my]
            for {set y $b} {$y < $h - $b} {incr y} {
                if {[$img get $x $y] ne $ref || [$img transparency get $x $y] != $tref} { return 0 }
            }
        }
        return 1
    }

    proc stretched {img} {
        variable cache
        variable extra
        if {[info exists cache($img)]} { return $cache($img) }
        set w [image width $img]
        set h [image height $img]
        set mx [expr {$w / 2}]
        set my [expr {$h / 2}]
        set new [image create photo -width [expr {$w + $extra}] -height [expr {$h + $extra}]]
        # (début source, fin source, début cible, fin cible) : avant, milieu répété, après.
        set cols [list [list 0 $mx 0 $mx] \
            [list $mx [expr {$mx + 1}] $mx [expr {$mx + $extra + 1}]] \
            [list [expr {$mx + 1}] $w [expr {$mx + $extra + 1}] [expr {$w + $extra}]]]
        set rows [list [list 0 $my 0 $my] \
            [list $my [expr {$my + 1}] $my [expr {$my + $extra + 1}]] \
            [list [expr {$my + 1}] $h [expr {$my + $extra + 1}] [expr {$h + $extra}]]]
        foreach c $cols {
            lassign $c sx0 sx1 dx0 dx1
            if {$sx1 <= $sx0} continue
            foreach r $rows {
                lassign $r sy0 sy1 dy0 dy1
                if {$sy1 <= $sy0} continue
                $new copy $img -from $sx0 $sy0 $sx1 $sy1 -to $dx0 $dy0 $dx1 $dy1 -compositingrule set
            }
        }
        set cache($img) $new
        return $new
    }

    proc element_create {name spec opts} {
        if {[llength $opts] % 2 || ![dict exists $opts -border]
                || [dict exists $opts -width] || [dict exists $opts -height]} {
            return {}
        }
        set b [tcl::mathfunc::max {*}[dict get $opts -border]]
        # Image de base puis paires {état image}.
        set images [list [lindex $spec 0]]
        foreach {state img} [lrange $spec 1 end] { lappend images $img }
        set base [lindex $spec 0]
        foreach img $images {
            if {[image width $img] != [image width $base] || [image height $img] != [image height $base]
                    || ![uniform $img $b]} {
                return {}
            }
        }
        set new [list [stretched $base]]
        foreach {state img} [lrange $spec 1 end] { lappend new $state [stretched $img] }
        return [list $new [concat $opts [list -width [image width $base] -height [image height $base]]]]
    }
}

rename ::ttk::style ::theme_perf::style
proc ::ttk::style {args} {
    if {[lrange $args 0 1] eq {element create} && [lindex $args 3] eq "image"} {
        set patched [::theme_perf::element_create [lindex $args 2] [lindex $args 4] [lrange $args 5 end]]
        if {$patched ne {}} {
            lassign $patched spec opts
            return [uplevel 1 [list ::theme_perf::style element create [lindex $args 2] image $spec {*}$opts]]
        }
    }
    # uplevel : les scripts -settings du thème doivent s'exécuter dans le contexte de l'appelant.
    return [uplevel 1 [list ::theme_perf::style {*}$args]]
}
"""


def install(root):
    """À appeler avant de charger le thème. Sans effet si l'interception échoue."""
    try:
        root.tk.eval(TCL_HOOK.replace("@EXTRA@", str(STRETCH_PX)))
        return True
    except Exception:
        return False


def uninstall(root):
    """Rend sa commande d'origine à ttk::style une fois le thème chargé (les images restent)."""
    try:
        root.tk.eval("""
            if {[namespace which ::theme_perf::style] ne ""} {
                rename ::ttk::style {}
                rename ::theme_perf::style ::ttk::style
            }
        """)
    except Exception:
        pass
