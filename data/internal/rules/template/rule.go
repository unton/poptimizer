package template

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"sync"
)

type Rule[R any] struct {
	name      string
	logger    *lgr.Logger
	repo      repo.ReadWrite[R]
	selector  Selector
	gateway   Gateway[R]
	validator Validator[R]
	append    bool
	ctxFunc   EventCtxFunc
}

func NewRule[R any](
	name string,
	logger *lgr.Logger,
	repo repo.ReadWrite[R],
	selector Selector,
	gateway Gateway[R],
	validator Validator[R],
	append bool,
	ctxFunc EventCtxFunc,
) Rule[R] {
	return Rule[R]{
		name:      name,
		logger:    logger,
		repo:      repo,
		selector:  selector,
		gateway:   gateway,
		validator: validator,
		append:    append,
		ctxFunc:   ctxFunc,
	}
}

func (r Rule[R]) Activate(in <-chan domain.Event, out chan<- domain.Event) {
	r.logger.Infof("%s: started", r.name)
	defer r.logger.Infof("%s: stopped", r.name)

	var wg sync.WaitGroup
	defer wg.Wait()

	for event := range in {
		wg.Add(1)

		event := event

		go func() {
			defer wg.Done()

			r.handleEvent(out, event)
		}()
	}

}

func (r Rule[R]) handleEvent(out chan<- domain.Event, event domain.Event) {
	ctx, cancel := r.ctxFunc()
	defer cancel()

	var wg sync.WaitGroup
	defer wg.Wait()

	ids, err := r.selector.Select(ctx, event)
	if err != nil {
		out <- domain.NewErrorOccurred(event, err)

		return
	}

	for _, id := range ids {
		id := id

		wg.Add(1)

		go func() {
			defer wg.Done()

			if newEvent := r.updateTableToVer(ctx, domain.NewVersion(id, event.Date())); newEvent != nil {
				out <- newEvent
			}

		}()
	}
}

func (r Rule[R]) updateTableToVer(ctx context.Context, ver domain.Version) domain.Event {
	table, err := r.repo.Get(ctx, ver)
	if err != nil {
		return domain.NewErrorOccurred(ver, err)
	}

	rows, err := r.gateway.Get(ctx, table, ver.Date())
	if err != nil {
		return domain.NewErrorOccurred(ver, err)
	}

	if len(rows) == 0 {
		return nil
	}

	err = r.validator(table, rows)
	if err != nil {
		return domain.NewErrorOccurred(ver, err)
	}

	if r.append {
		err = r.repo.Append(ctx, domain.Table[R]{ver, rows[1:]})
	} else {
		err = r.repo.Replace(ctx, domain.Table[R]{ver, rows})
	}

	if err != nil {
		return domain.NewErrorOccurred(ver, err)
	}

	return domain.NewUpdateCompleted(ver)
}