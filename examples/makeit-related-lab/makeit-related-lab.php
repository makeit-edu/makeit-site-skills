<?php
/**
 * Plugin Name: 메킷 관련 글 연습
 * Description: 단축코드를 넣은 글에서만 같은 카테고리의 공개 글을 카드로 보여주는 독립 실습 예제.
 * Version: 0.1.0
 * Requires at least: 6.4
 * Requires PHP: 7.4
 * Author: MAKEIT
 * License: MIT
 * Text Domain: makeit-related-lab
 * Update URI: false
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Load local styles only for posts using the exercise shortcode.
 */
function makeit_related_lab_assets() {
	if ( ! is_singular( 'post' ) ) {
		return;
	}
	$post = get_queried_object();
	if ( $post instanceof WP_Post && has_shortcode( $post->post_content, 'makeit_related_lab' ) ) {
		wp_enqueue_style( 'makeit-related-lab', plugins_url( 'cards.css', __FILE__ ), array(), '0.1.0' );
	}
}
add_action( 'wp_enqueue_scripts', 'makeit_related_lab_assets' );

/**
 * Render related public posts without changing global post state or stored content.
 *
 * @return string
 */
function makeit_related_lab_render() {
	if ( is_admin() || is_feed() || ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() ) {
		return '';
	}
	$post_id = get_the_ID();
	if ( post_password_required( $post_id ) ) {
		return '';
	}
	$categories = wp_get_post_categories( $post_id );
	if ( is_wp_error( $categories ) || empty( $categories ) ) {
		return '';
	}
	$related = get_posts(
		array(
			'post_type'           => 'post',
			'post_status'         => 'publish',
			'has_password'        => false,
			'post__not_in'        => array( $post_id ),
			'category__in'        => array_map( 'absint', $categories ),
			'numberposts'         => 6,
			'orderby'            => array( 'date' => 'DESC', 'ID' => 'DESC' ),
			'ignore_sticky_posts' => true,
		)
	);
	if ( empty( $related ) ) {
		return '';
	}
	$html = '<section class="makeit-related-lab" aria-label="함께 읽을 글"><h2>함께 읽을 글</h2><ul class="makeit-related-lab__grid">';
	foreach ( $related as $item ) {
		$title = get_the_title( $item );
		if ( '' === trim( $title ) ) {
			$title = '제목 없는 글';
		}
		$image = get_the_post_thumbnail(
			$item,
			'medium_large',
			array( 'class' => 'makeit-related-lab__image', 'loading' => 'lazy', 'alt' => '' )
		);
		if ( '' === $image ) {
			$image = '<span class="makeit-related-lab__placeholder" aria-hidden="true">함께 읽어요</span>';
		}
		$html .= '<li><a class="makeit-related-lab__card" href="' . esc_url( get_permalink( $item ) ) . '">';
		$html .= $image . '<span class="makeit-related-lab__title">' . esc_html( $title ) . '</span></a></li>';
	}
	return $html . '</ul></section>';
}
add_shortcode( 'makeit_related_lab', 'makeit_related_lab_render' );
