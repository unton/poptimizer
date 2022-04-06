package edit

import (
	"errors"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

const _sessionID = `SessionID`

type handler struct {
	logger *lgr.Logger

	service *services.RawDivUpdate

	index  *template.Template
	add    *template.Template
	reload *template.Template
	save   *template.Template
}

func (h *handler) handleIndex(responseWriter http.ResponseWriter, request *http.Request) {
	ticker := chi.URLParam(request, "ticker")
	ctx := request.Context()

	model, err := h.service.GetByTicker(ctx, ticker)
	if err != nil {
		h.logger.Warnf("Server: can't load dividends -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)

		return
	}

	cookie := http.Cookie{
		Name:     _sessionID,
		Value:    model.SessionID,
		Path:     request.RequestURI,
		MaxAge:   0,
		Secure:   false,
		HttpOnly: true,
		SameSite: http.SameSiteStrictMode,
	}

	http.SetCookie(responseWriter, &cookie)
	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.index.Execute(responseWriter, model); err != nil {
		h.logger.Warnf("Server: can't render index template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleAddRow(responseWriter http.ResponseWriter, request *http.Request) {
	cookie, err := request.Cookie(_sessionID)
	if errors.Is(err, http.ErrNoCookie) {
		h.logger.Warnf("Server: no cookie in request")
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	if err := request.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	row, err := h.service.AddRow(
		cookie.Value,
		request.PostForm.Get("date"),
		request.PostForm.Get("value"),
		request.PostForm.Get("currency"),
	)
	if err != nil {
		h.logger.Warnf("Server: can't add row -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.add.Execute(responseWriter, row); err != nil {
		h.logger.Warnf("Server: can't render add template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleReload(responseWriter http.ResponseWriter, request *http.Request) {
	cookie, err := request.Cookie(_sessionID)
	if errors.Is(err, http.ErrNoCookie) {
		h.logger.Warnf("Server: no cookie in request")
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	div, err := h.service.Reload(request.Context(), cookie.Value)
	if err != nil {
		h.logger.Warnf("Server: can't reload page -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.reload.Execute(responseWriter, div); err != nil {
		h.logger.Warnf("Server: can't render reload template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleSave(responseWriter http.ResponseWriter, request *http.Request) {
	cookie, err := request.Cookie(_sessionID)
	if errors.Is(err, http.ErrNoCookie) {
		h.logger.Warnf("Server: no cookie in request")
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	status := h.service.Save(request.Context(), cookie.Value)

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.save.Execute(responseWriter, status); err != nil {
		h.logger.Warnf("Server: can't render save template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}
